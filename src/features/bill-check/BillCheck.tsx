import { useCallback, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { checkFile } from '../../core/api/documents';
import { formatDate } from '../../core/api/http';
import { DocumentViewer } from '../../core/components/DocumentViewer';
import { Icon } from '../../core/components/Icon';
import { PriceContext } from '../../core/components/PriceContext';
import { ClaimBlock, More } from '../../core/components/SourceLinks';
import type { Span } from '../../core/lib/highlight';
import { useAsync } from '../../core/lib/useAsync';
import {
  billSamplePdfUrl,
  checkUploads,
  fetchBillSamples,
  formatCents,
  runBillSample,
  type BillCheckResult,
  type BillCheckSample,
  type Flag,
  type LineItem,
  type LineItemExtraction,
} from './api';

type State = { status: 'idle' } | { status: 'loading'; label: string } | { status: 'error'; message: string } | { status: 'ready'; result: BillCheckResult };

/** Highlights every service line and total on a document; ids are the line ids ("bill-2") or "<doc>-total-<key>". */
function spansFor(doc: LineItemExtraction, prefix: 'eob' | 'bill'): Map<number, Span[]> {
  const map = new Map<number, Span[]>();
  const add = (page: number, span: Span) => map.set(page, [...(map.get(page) ?? []), span]);
  doc.line_items.forEach((i) => add(i.citation.page, { id: i.id, start: i.citation.start, end: i.citation.end }));
  doc.totals.forEach((t) => add(t.citation.page, { id: `${prefix}-total-${t.key.replace(/_/g, '-')}`, start: t.citation.start, end: t.citation.end }));
  return map;
}

function serviceLabel(item: LineItem) {
  return `${item.description}${item.code ? ` (${item.code})` : ''}`;
}

// ------------------------------------------------------------------ choosing documents

function SampleList({ onPick, disabled }: { onPick: (s: BillCheckSample) => void; disabled: boolean }) {
  const [state, retry] = useAsync(fetchBillSamples);
  if (state.status === 'loading') {
    return (
      <div aria-busy="true">
        <span className="skeleton skeleton-line" />
        <span className="skeleton skeleton-line short" />
        <span className="visually-hidden">Loading samples…</span>
      </div>
    );
  }
  if (state.status === 'error') {
    return (
      <div className="status-card status-error" role="alert">
        <p>
          <strong>Samples are unavailable.</strong> {state.message}
        </p>
        <button type="button" className="btn btn-quiet" onClick={retry}>
          <Icon name="refresh" size={16} /> Try again
        </button>
      </div>
    );
  }
  return (
    <ul className="sample-list">
      {state.data.map((s) => (
        <li key={s.id} className="sample">
          <div>
            <h3>{s.title}</h3>
            <p>{s.description}</p>
          </div>
          <div className="sample-actions">
            <button type="button" className="btn btn-secondary" disabled={disabled} onClick={() => onPick(s)}>
              Compare this sample
            </button>
            <a className="text-link" href={billSamplePdfUrl(s.id, 'eob')} download={s.eob_filename}>
              EOB PDF
            </a>
            <a className="text-link" href={billSamplePdfUrl(s.id, 'bill')} download={s.bill_filename}>
              Bill PDF
            </a>
          </div>
        </li>
      ))}
    </ul>
  );
}

function FilePick({ id, label, hint, file, onChange, disabled }: { id: string; label: string; hint: string; file: File | null; onChange: (f: File | null) => void; disabled: boolean }) {
  return (
    <div className="file-pick">
      <label htmlFor={id} className="file-pick-label">
        {label}
      </label>
      <p className="file-pick-hint" id={`${id}-hint`}>
        {hint}
      </p>
      <input
        id={id}
        type="file"
        accept=".pdf,.txt,application/pdf,text/plain"
        aria-describedby={`${id}-hint`}
        disabled={disabled}
        onChange={(e) => {
          onChange(e.target.files?.[0] ?? null);
        }}
      />
      {file && <p className="file-pick-chosen">Selected: {file.name}</p>}
    </div>
  );
}

function UploadPanel({ onCompare, disabled }: { onCompare: (eob: File, bill: File) => void; disabled: boolean }) {
  const [eob, setEob] = useState<File | null>(null);
  const [bill, setBill] = useState<File | null>(null);
  const [problem, setProblem] = useState<string | null>(null);

  const submit = () => {
    if (!eob || !bill) {
      setProblem('Add both documents: your EOB and the bill.');
      return;
    }
    const issue = (checkFile(eob) && `Your EOB: ${checkFile(eob)}`) || (checkFile(bill) && `Your bill: ${checkFile(bill)}`);
    if (issue) {
      setProblem(issue);
      return;
    }
    setProblem(null);
    onCompare(eob, bill);
  };

  return (
    <div className="dropzone upload-pair">
      <FilePick
        id="eob-file"
        label="Your Explanation of Benefits (EOB)"
        hint="From your insurer. It usually says “This is not a bill.”"
        file={eob}
        onChange={setEob}
        disabled={disabled}
      />
      <FilePick id="bill-file" label="The bill" hint="From the doctor, hospital or other provider, for the same visit." file={bill} onChange={setBill} disabled={disabled} />
      {problem && (
        <p className="form-error" role="alert">
          {problem}
        </p>
      )}
      <button type="button" className="btn btn-primary" onClick={submit} disabled={disabled}>
        Compare them
      </button>
      <p className="dropzone-hint">PDF or .txt, up to 4 MB each. Text-based PDFs only; scanned images can’t be read yet.</p>
      <p className="dropzone-warning">
        <Icon name="alert" size={14} /> This prototype is not approved for real health information. Please use a sample.
      </p>
    </div>
  );
}

// ------------------------------------------------------------------ results

function LineButtons({ flag, onCite, activeId, items }: { flag: Flag; onCite: (id: string) => void; activeId: string | null; items: Map<string, LineItem> }) {
  const ids = [...flag.bill_item_ids, ...flag.eob_item_ids];
  if (!ids.length) return null;
  return (
    <div className="cite-buttons" role="group" aria-label="Where this appears">
      {ids.map((id) => {
        const item = items.get(id);
        const where = id.startsWith('eob') ? 'EOB' : 'Bill';
        return (
          <button key={id} type="button" className={activeId === id ? 'cite-button active' : 'cite-button'} aria-pressed={activeId === id} onClick={() => onCite(id)}>
            <Icon name="doc" size={14} /> {where}: {item ? serviceLabel(item) : 'line'}
          </button>
        );
      })}
    </div>
  );
}

function FlagCard({ flag, onCite, activeId, items }: { flag: Flag; onCite: (id: string) => void; activeId: string | null; items: Map<string, LineItem> }) {
  const headingId = `flag-${flag.id}`;
  return (
    <article className={flag.level === 'ask' ? 'field-card flag-ask' : 'field-card flag-info'} aria-labelledby={headingId}>
      <header className="field-head">
        <h3 id={headingId}>{flag.title}</h3>
        {flag.practical && <span className="badge badge-guidance">Practical suggestion</span>}
      </header>
      <p>{flag.detail}</p>
      {flag.kind === 'denied_on_eob' && (
        <p>
          <Link to="/navigator" className="text-link">
            Open the Denial Navigator <Icon name="arrow" size={16} />
          </Link>
        </p>
      )}
      <LineButtons flag={flag} onCite={onCite} activeId={activeId} items={items} />
      {flag.claims.map((c) => (
        <ClaimBlock key={c.id} claim={c} />
      ))}
    </article>
  );
}

function LineTable({ result }: { result: BillCheckResult }) {
  const { eob, bill, comparison } = result;
  const eobById = new Map(eob.line_items.map((i) => [i.id, i]));
  const matchFor = new Map(comparison.matches.map((m) => [m.bill_item_id, m.eob_item_id]));
  const matchedEob = new Set(comparison.matches.map((m) => m.eob_item_id));
  const flagged = new Map<string, string>();
  comparison.flags.forEach((f) => {
    if (f.kind === 'possible_duplicate') f.bill_item_ids.slice(1).forEach((id) => flagged.set(id, 'Repeats another line'));
    if (f.kind === 'not_on_eob') f.bill_item_ids.forEach((id) => flagged.set(id, 'Not on this EOB'));
    if (f.kind === 'charge_differs') f.bill_item_ids.forEach((id) => flagged.set(id, 'Charge differs'));
  });
  const money = (c: number | undefined) => (c === undefined ? '—' : formatCents(c));

  return (
    // Focusable so keyboard users can scroll the table sideways on a narrow screen (axe: scrollable-region-focusable).
    // eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex
    <div className="table-scroll" role="region" aria-labelledby="line-table-caption" tabIndex={0}>
      <table className="line-table">
        <caption id="line-table-caption">Each line on the bill, next to the EOB</caption>
        <thead>
          <tr>
            <th scope="col">Date</th>
            <th scope="col">Service</th>
            <th scope="col">Bill charge</th>
            <th scope="col">EOB charge</th>
            <th scope="col">EOB: you owe</th>
            <th scope="col">Status</th>
          </tr>
        </thead>
        <tbody>
          {bill.line_items.map((b) => {
            const e = eobById.get(matchFor.get(b.id) ?? '');
            const status = flagged.get(b.id) ?? (e ? (e.status === 'denied' ? 'Denied on EOB' : 'Matches EOB') : 'Not on this EOB');
            return (
              <tr key={b.id}>
                <td>{b.service_date ? formatDate(b.service_date) : '—'}</td>
                <th scope="row">{serviceLabel(b)}</th>
                <td>{money(b.amounts.billed)}</td>
                <td>{money(e?.amounts.billed)}</td>
                <td>{money(e?.amounts.patient_owes)}</td>
                <td>{status}</td>
              </tr>
            );
          })}
          {eob.line_items
            .filter((e) => !matchedEob.has(e.id))
            .map((e) => (
              <tr key={e.id}>
                <td>{e.service_date ? formatDate(e.service_date) : '—'}</td>
                <th scope="row">{serviceLabel(e)}</th>
                <td>—</td>
                <td>{money(e.amounts.billed)}</td>
                <td>{money(e.amounts.patient_owes)}</td>
                <td>On EOB only</td>
              </tr>
            ))}
        </tbody>
      </table>
    </div>
  );
}

function Results({ result, onDelete }: { result: BillCheckResult; onDelete: () => void }) {
  const [activeId, setActiveId] = useState<string | null>(null);
  const { eob, bill, comparison } = result;
  const eobSpans = useMemo(() => spansFor(eob, 'eob'), [eob]);
  const billSpans = useMemo(() => spansFor(bill, 'bill'), [bill]);
  const items = useMemo(() => new Map([...eob.line_items, ...bill.line_items].map((i) => [i.id, i])), [eob, bill]);
  const ask = comparison.flags.filter((f) => f.level === 'ask');
  const info = comparison.flags.filter((f) => f.level === 'info');
  const synthetic = eob.document.synthetic && bill.document.synthetic;
  const flaggedIds = new Set(ask.flatMap((f) => [...f.bill_item_ids, ...f.eob_item_ids]));

  return (
    <section aria-labelledby="results-heading" className="results">
      <div className="results-head">
        <div>
          <p className="eyebrow">Your bill and EOB, side by side</p>
          <h2 id="results-heading">
            {comparison.matches.length} of {bill.line_items.length} bill {bill.line_items.length === 1 ? 'line matches' : 'lines match'} the EOB
          </h2>
          <p className="muted">
            {eob.document.name} · {bill.document.name}
            {synthetic && <span className="badge badge-synthetic">Synthetic sample</span>}
          </p>
        </div>
        <button type="button" className="btn btn-secondary" onClick={onDelete}>
          Delete both documents
        </button>
      </div>

      <p className="retention">
        <Icon name="lock" size={16} /> Not saved. Delete them any time.
      </p>
      <More summary="How your files are handled">
        <p>{eob.retention}</p>
      </More>

      {[...eob.warnings.map((w) => `EOB: ${w}`), ...bill.warnings.map((w) => `Bill: ${w}`)].map((w) => (
        <div key={w} className="callout callout-tight" role="alert">
          <Icon name="alert" size={20} className="callout-icon" />
          <p>{w}</p>
        </div>
      ))}

      <dl className="status-grid bill-summary">
        <div>
          <dt>The EOB says you owe</dt>
          <dd>{comparison.eob_patient_owes_cents === null ? 'Not found' : formatCents(comparison.eob_patient_owes_cents)}</dd>
        </div>
        <div>
          <dt>The bill asks for</dt>
          <dd>{comparison.bill_amount_due_cents === null ? 'Not found' : formatCents(comparison.bill_amount_due_cents)}</dd>
        </div>
        <div>
          <dt>Worth asking about</dt>
          <dd>{ask.length}</dd>
        </div>
      </dl>
      <p className="muted bill-disclaimer">Differences to ask about, not proof of a mistake.</p>
      <More summary="What this means">
        <p>{comparison.disclaimer}</p>
      </More>

      <div className="results-grid">
        <div className="results-fields">
          <h3 className="card-heading">Worth asking about</h3>
          {ask.length ? (
            ask.map((f) => <FlagCard key={f.id} flag={f} onCite={setActiveId} activeId={activeId} items={items} />)
          ) : (
            <p className="field-card">Nothing stood out: each bill line matches the EOB, and the amount due matches what the EOB says you owe.</p>
          )}
          {info.length > 0 && (
            <>
              <h3 className="card-heading">Good to know</h3>
              {info.map((f) => (
                <FlagCard key={f.id} flag={f} onCite={setActiveId} activeId={activeId} items={items} />
              ))}
            </>
          )}

          <h3 className="card-heading">Line by line</h3>
          <LineTable result={result} />

          <PriceContext
            title="Price context for these services"
            intro="Charges from your bill next to what Medicare pays for the same service, for services PatientShield has amounts for."
            rows={bill.line_items.filter((i) => i.code && i.amounts.billed !== undefined).map((i) => ({ key: i.id, code: i.code!, chargeCents: i.amounts.billed }))}
          />

          <h3 className="card-heading">Before you pay</h3>
          {comparison.next_steps.map((c) => (
            <ClaimBlock key={c.id} claim={c} />
          ))}
        </div>
        <div className="results-doc bill-docs">
          <h3 className="card-heading">Your EOB</h3>
          <DocumentViewer
            pages={eob.pages}
            spansByPage={eobSpans}
            activeId={activeId}
            isWarning={(id) => flaggedIds.has(id)}
            label="Your EOB, with each service line highlighted"
            documentName="EOB"
          />
          <h3 className="card-heading">Your bill</h3>
          <DocumentViewer
            pages={bill.pages}
            spansByPage={billSpans}
            activeId={activeId}
            isWarning={(id) => flaggedIds.has(id)}
            label="Your bill, with each service line highlighted"
            documentName="Bill"
          />
        </div>
      </div>
    </section>
  );
}

// ------------------------------------------------------------------ page

export function BillCheck() {
  const [state, setState] = useState<State>({ status: 'idle' });
  const controller = useRef<AbortController | null>(null);
  const statusRef = useRef<HTMLDivElement>(null);

  const run = useCallback(async (label: string, task: (signal: AbortSignal) => Promise<BillCheckResult>) => {
    controller.current?.abort();
    const ctrl = new AbortController();
    controller.current = ctrl;
    setState({ status: 'loading', label });
    try {
      setState({ status: 'ready', result: await task(ctrl.signal) });
    } catch (err) {
      if ((err as Error).name !== 'AbortError') setState({ status: 'error', message: (err as Error).message });
    } finally {
      statusRef.current?.focus();
    }
  }, []);

  const onDelete = () => {
    controller.current?.abort();
    setState({ status: 'idle' });
  };

  const busy = state.status === 'loading';

  return (
    <div className="container page">
      <p className="eyebrow">Bill check</p>
      <h1>Compare a bill with your EOB</h1>
      <p className="lede">Add your EOB and the bill. We line them up and flag what’s worth asking about.</p>

      <div ref={statusRef} tabIndex={-1} className="status-region" aria-live="polite">
        {state.status === 'loading' && (
          <p className="loading" role="status">
            <span className="spinner" aria-hidden="true" /> {state.label}
          </p>
        )}
        {state.status === 'error' && (
          <div className="status-card status-error" role="alert">
            <p>{state.message}</p>
            <button type="button" className="btn btn-quiet" onClick={() => setState({ status: 'idle' })}>
              Try again
            </button>
          </div>
        )}
      </div>

      {state.status === 'ready' ? (
        <Results result={state.result} onDelete={onDelete} />
      ) : (
        <div className="choose-grid">
          <section aria-labelledby="upload-heading">
            <h2 id="upload-heading" className="section-title">
              Add your EOB and bill
            </h2>
            <UploadPanel disabled={busy} onCompare={(eob, bill) => void run('Reading your EOB and bill…', (signal) => checkUploads(eob, bill, signal))} />
          </section>
          <section aria-labelledby="samples-heading">
            <h2 id="samples-heading" className="section-title">
              Or try a synthetic sample
            </h2>
            <SampleList disabled={busy} onPick={(s) => void run(`Comparing “${s.title}”…`, (signal) => runBillSample(s.id, signal))} />
          </section>
        </div>
      )}
    </div>
  );
}
