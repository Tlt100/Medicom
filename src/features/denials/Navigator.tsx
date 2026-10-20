import { useCallback, useMemo, useRef, useState, type DragEvent } from 'react';
import { ActionPlanView } from './ActionPlanView';
import { DocumentViewer } from '../../core/components/DocumentViewer';
import { FieldCard } from './FieldCard';
import { Icon } from '../../core/components/Icon';
import { More } from '../../core/components/SourceLinks';
import { PlanResult } from '../../core/components/PlanResult';
import { SituationForm } from './SituationForm';
import { Triage } from '../../core/components/Triage';
import { checkFile } from '../../core/api/documents';
import { extractSample, fetchSamples, samplePdfUrl, uploadDocument, type Extraction, type Sample, type ActionPlan, type Situation, buildPlan } from './api';
import { type TriageResult } from '../../core/api/triage';
import { letterFacts } from './letterFacts';
import { isSignalCitation, letterSpans } from './letterSpans';
import type { Answers } from '../../core/lib/triage';
import { useAsync } from '../../core/lib/useAsync';

type State =
  | { status: 'idle' }
  | { status: 'loading'; label: string }
  | { status: 'error'; message: string }
  | { status: 'ready'; result: Extraction };

const PRIMARY = ['denial_reason', 'appeal_instructions', 'appeal_deadline', 'external_review_deadline'];

type View = 'letter' | 'triage' | 'plan' | 'action';

const STEPS: { view: View; label: string; note?: string }[] = [
  { view: 'letter', label: 'Add your letter' },
  { view: 'triage', label: 'Identify your plan type' },
  { view: 'plan', label: 'What applies to your plan' },
  { view: 'action', label: 'Your action plan' },
];

function Steps({ view }: { view: View }) {
  const currentIndex = STEPS.findIndex((s) => s.view === view);
  return (
    <ol className="stepper" aria-label="Denial Navigator steps">
      {STEPS.map((s, i) => (
        <li key={s.view} className={i === currentIndex ? 'current' : i < currentIndex ? 'done' : undefined} aria-current={i === currentIndex ? 'step' : undefined}>
          <span>{i + 1}</span> {s.label}
        </li>
      ))}
    </ol>
  );
}

function SampleList({ onPick, disabled }: { onPick: (s: Sample) => void; disabled: boolean }) {
  const [state, retry] = useAsync(fetchSamples);
  if (state.status === 'loading') {
    return (
      <div aria-busy="true">
        <span className="skeleton skeleton-line" />
        <span className="skeleton skeleton-line short" />
        <span className="visually-hidden">Loading sample letters…</span>
      </div>
    );
  }
  if (state.status === 'error') {
    return (
      <div className="status-card status-error" role="alert">
        <p>
          <strong>Sample letters are unavailable.</strong> {state.message}
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
              Read this sample
            </button>
            <a className="text-link" href={samplePdfUrl(s.id)} download={s.filename}>
              Download PDF
            </a>
          </div>
        </li>
      ))}
    </ul>
  );
}

function UploadPanel({ onFile, disabled }: { onFile: (f: File) => void; disabled: boolean }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file && !disabled) onFile(file);
  };

  return (
    <div
      className={dragging ? 'dropzone dragging' : 'dropzone'}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
    >
      <Icon name="upload" size={28} className="dropzone-icon" />
      <p className="dropzone-title">Drop a denial letter here, or</p>
      <label className="btn btn-primary">
        Choose a file
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.txt,application/pdf,text/plain"
          className="visually-hidden"
          disabled={disabled}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) onFile(file);
            e.target.value = '';
          }}
        />
      </label>
      <p className="dropzone-hint">PDF or .txt, up to 4 MB. Text-based PDFs only; scanned images can’t be read yet.</p>
      <p className="dropzone-warning">
        <Icon name="alert" size={14} /> This prototype is not approved for real health information. Please use a sample letter.
      </p>
    </div>
  );
}

function Results({ result, onDelete, onContinue }: { result: Extraction; onDelete: () => void; onContinue: () => void }) {
  const [activeId, setActiveId] = useState<string | null>(null);
  const spans = useMemo(() => letterSpans(result), [result]);
  const primary = result.fields.filter((f) => PRIMARY.includes(f.key));
  const details = result.fields.filter((f) => !PRIMARY.includes(f.key));
  const hints = result.signals.filter((s) => s.kind === 'plan-type');
  const urgent = result.signals.find((s) => s.kind === 'urgent');
  const found = result.fields.filter((f) => f.status === 'found').length;

  return (
    <section aria-labelledby="results-heading" className="results">
      <div className="results-head">
        <div>
          <p className="eyebrow">Step 1 · What your letter says</p>
          <h2 id="results-heading">{result.document.name}</h2>
          <p className="muted">
            {result.document.page_count} page{result.document.page_count === 1 ? '' : 's'} · {result.document.kind.toUpperCase()} · {found} of{' '}
            {result.fields.length} details found
            {result.document.synthetic && <span className="badge badge-synthetic">Synthetic sample</span>}
          </p>
        </div>
        <button type="button" className="btn btn-secondary" onClick={onDelete}>
          Delete this letter
        </button>
      </div>

      <p className="retention">
        <Icon name="lock" size={16} /> Not saved. Delete it any time.
      </p>
      <More summary="How your file is handled">
        <p>{result.retention}</p>
      </More>

      {result.warnings.map((w) => (
        <div key={w} className="callout callout-tight" role="alert">
          <Icon name="alert" size={20} className="callout-icon" />
          <p>{w}</p>
        </div>
      ))}

      {urgent && (
        <div className="callout callout-tight">
          <Icon name="alert" size={20} className="callout-icon" />
          <p>
            Your letter mentions expedited or urgent appeals. If waiting could seriously harm your health, contact the plan now and ask for an
            expedited appeal. For emergencies, call 911.
          </p>
        </div>
      )}

      <div className="results-grid">
        <div className="results-fields">
          <h3 className="card-heading">Key details</h3>
          {primary.map((f) => (
            <FieldCard key={f.key} field={f} activeId={activeId} onCite={setActiveId} />
          ))}
          <h3 className="card-heading">Letter details</h3>
          {details.map((f) => (
            <FieldCard key={f.key} field={f} activeId={activeId} onCite={setActiveId} />
          ))}

          {hints.length > 0 && (
            <div className="hint-box">
              <h3 className="card-heading">Clues about your plan type</h3>
              <p className="muted">
                These are words found in the letter, not a conclusion. You’ll confirm your plan type in the next step, because it decides
                which appeal rules apply.
              </p>
              <ul className="hint-list">
                {hints.map((h) => (
                  <li key={h.code}>
                    <strong>{h.label}</strong>
                    <span className="hint-quote">
                      “{h.citations[0]?.quote.replace(/\s+/g, ' ')}” · page {h.citations[0]?.page}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="next-step">
            <h3>Next: identify your plan type</h3>
            <p className="muted">
              Appeal rights depend on whether your plan is New Jersey-regulated, self-funded, Medicaid, Medicare, or a marketplace plan. A few
              questions will sort it out.
            </p>
            <button type="button" className="btn btn-primary" onClick={onContinue}>
              Identify my plan type <Icon name="arrow" size={18} />
            </button>
          </div>
        </div>
        <div className="results-doc">
          <h3 className="card-heading">Your letter</h3>
          <DocumentViewer
            pages={result.pages}
            spansByPage={spans}
            activeId={activeId}
            isWarning={isSignalCitation}
            label="Your letter, with cited passages highlighted"
          />
        </div>
      </div>
    </section>
  );
}

export function Navigator() {
  const [state, setState] = useState<State>({ status: 'idle' });
  const [view, setView] = useState<View>('letter');
  const [plan, setPlan] = useState<{ result: TriageResult; answers: Answers } | null>(null);
  const [situation, setSituation] = useState<Situation | undefined>(undefined);
  const [action, setAction] = useState<ActionPlan | null>(null);
  const [building, setBuilding] = useState(false);
  const [buildError, setBuildError] = useState<string | null>(null);
  const controller = useRef<AbortController | null>(null);
  const topRef = useRef<HTMLHeadingElement>(null);
  const statusRef = useRef<HTMLDivElement>(null);

  const run = useCallback(async (label: string, task: (signal: AbortSignal) => Promise<Extraction>) => {
    controller.current?.abort();
    const ctrl = new AbortController();
    controller.current = ctrl;
    setState({ status: 'loading', label });
    try {
      const result = await task(ctrl.signal);
      setState({ status: 'ready', result });
      setPlan(null);
      setSituation(undefined);
      setAction(null);
      setView('letter');
    } catch (err) {
      if ((err as Error).name !== 'AbortError') setState({ status: 'error', message: (err as Error).message });
    } finally {
      statusRef.current?.focus();
    }
  }, []);

  const onFile = (file: File) => {
    const problem = checkFile(file);
    if (problem) {
      setState({ status: 'error', message: problem });
      statusRef.current?.focus();
      return;
    }
    void run(`Reading ${file.name}…`, (signal) => uploadDocument(file, signal));
  };

  const onDelete = () => {
    controller.current?.abort();
    setState({ status: 'idle' });
    setPlan(null);
    setSituation(undefined);
    setAction(null);
    setView('letter');
  };

  const onBuild = async (s: Situation) => {
    if (state.status !== 'ready' || !plan) return;
    setSituation(s);
    setBuilding(true);
    setBuildError(null);
    try {
      setAction(await buildPlan({ answers: plan.answers, letter: letterFacts(state.result), situation: s }));
      go('action');
    } catch (err) {
      setBuildError((err as Error).message);
    } finally {
      setBuilding(false);
    }
  };

  const go = (next: View) => {
    setView(next);
    window.scrollTo?.(0, 0);
    topRef.current?.focus();
  };

  const signals = useMemo(
    () => (state.status === 'ready' ? state.result.signals.filter((s) => s.kind === 'plan-type').map((s) => s.code) : []),
    [state],
  );

  const busy = state.status === 'loading';

  return (
    <div className="container page">
      <p className="eyebrow">Denial Navigator</p>
      <h1 ref={topRef} tabIndex={-1}>
        Understand your denial letter
      </h1>
      <p className="lede">Upload a letter or try a sample. Every detail links to where it appears.</p>
      <Steps view={view} />

      <div ref={statusRef} tabIndex={-1} className="status-region" aria-live="polite">
        {state.status === 'loading' && (
          <p className="loading" role="status">
            <span className="spinner" aria-hidden="true" /> {state.label}
          </p>
        )}
        {state.status === 'error' && (
          <div className="status-card status-error" role="alert">
            <p>
              <strong>We couldn’t read that file.</strong> {state.message}
            </p>
            <button type="button" className="btn btn-quiet" onClick={() => setState({ status: 'idle' })}>
              Try another file
            </button>
          </div>
        )}
      </div>

      {state.status === 'ready' && view === 'triage' ? (
        <section aria-labelledby="triage-heading">
          <p className="eyebrow">Step 2 · Your plan type</p>
          <h2 id="triage-heading">A few questions about your coverage</h2>
          <p className="muted">Your answers decide which appeal rules apply. Not sure? Say so.</p>
          <Triage
            signals={signals}
            initialAnswers={plan?.answers}
            onBack={() => go('letter')}
            onDone={(result, answers) => {
              setPlan({ result, answers });
              setAction(null);
              go('plan');
            }}
          />
        </section>
      ) : state.status === 'ready' && view === 'action' && action ? (
        <ActionPlanView plan={action} onEditSituation={() => go('plan')} onBackToLetter={() => go('letter')} />
      ) : state.status === 'ready' && view === 'plan' && plan ? (
        <PlanResult result={plan.result} onChangeAnswers={() => go('triage')} onBackToLetter={() => go('letter')}>
          <SituationForm
            letterDate={letterFacts(state.result).letter_date}
            initial={situation}
            submitting={building}
            error={buildError}
            onSubmit={(s) => void onBuild(s)}
          />
        </PlanResult>
      ) : state.status === 'ready' ? (
        <Results result={state.result} onDelete={onDelete} onContinue={() => go(action ? 'action' : plan ? 'plan' : 'triage')} />
      ) : (
        <div className="choose-grid">
          <section aria-labelledby="upload-heading">
            <h2 id="upload-heading" className="section-title">
              Upload a letter
            </h2>
            <UploadPanel onFile={onFile} disabled={busy} />
          </section>
          <section aria-labelledby="samples-heading">
            <h2 id="samples-heading" className="section-title">
              Or try a synthetic sample
            </h2>
            <SampleList disabled={busy} onPick={(s) => void run(`Reading “${s.title}”…`, (signal) => extractSample(s.id, signal))} />
          </section>
        </div>
      )}
    </div>
  );
}
