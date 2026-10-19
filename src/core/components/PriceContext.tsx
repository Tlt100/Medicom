import { useId, useState } from 'react';
import { formatDate } from '../api/http';
import { fetchBenchmarks, localityFor, timesMedicare, type Benchmarks, type BenchmarkRate } from '../api/benchmarks';
import { formatCents, parseDollars } from '../lib/money';
import { useAsync } from '../lib/useAsync';
import { Icon } from './Icon';
import { ClaimBlock } from './SourceLinks';

export interface PriceRow {
  key: string;
  code: string;
  /** A charge already known (from a bill). When absent, the person can type one. */
  chargeCents?: number;
}

function Amount({ cents }: { cents: number | null }) {
  return <>{cents === null ? '—' : formatCents(cents)}</>;
}

function Row({ row, rate, b, locality }: { row: PriceRow; rate: BenchmarkRate; b: Benchmarks; locality: string | null }) {
  const [charge, setCharge] = useState('');
  const [published, setPublished] = useState('');
  const id = useId();
  const chargeCents = row.chargeCents ?? parseDollars(charge);
  const publishedCents = parseDollars(published);
  const shown = locality ? [locality] : b.localities.map((l) => l.id);
  const amounts = shown.map((l) => rate.amounts_cents[l]!).filter((n) => n !== undefined);
  const name = (l: string) => b.localities.find((x) => x.id === l)?.name ?? l;

  const compare = (cents: number | null, what: string) => {
    if (cents === null || !amounts.length || amounts.some((a) => a === 0)) return null;
    const times = amounts.map((a) => timesMedicare(cents, a));
    const lo = Math.min(...times);
    const hi = Math.max(...times);
    return `${what} is about ${lo === hi ? lo : `${lo} to ${hi}`} times the Medicare amount.`;
  };

  return (
    <tr>
      <th scope="row">
        {rate.label} <span className="muted">({rate.code})</span>
        <p className="price-covers">{rate.covers}</p>
      </th>
      <td>
        {row.chargeCents !== undefined ? (
          formatCents(row.chargeCents)
        ) : (
          <input aria-label={`Charge on your bill for ${rate.label}`} inputMode="decimal" value={charge} onChange={(e) => setCharge(e.target.value)} />
        )}
      </td>
      <td>
        <input
          aria-label={`Hospital’s published price for ${rate.label}`}
          aria-describedby={`${id}-pub`}
          inputMode="decimal"
          value={published}
          onChange={(e) => setPublished(e.target.value)}
        />
        <span id={`${id}-pub`} className="visually-hidden">
          Optional. From the hospital’s price list, for example its discounted cash price.
        </span>
      </td>
      <td>
        {shown.map((l) => (
          <div key={l}>
            <Amount cents={rate.amounts_cents[l] ?? null} />
            {shown.length > 1 && <span className="muted"> {name(l)}</span>}
          </div>
        ))}
      </td>
      <td aria-live="polite">
        {rate.comparable
          ? [compare(chargeCents, 'The charge'), compare(publishedCents, 'The published price')].filter(Boolean).join(' ') || '—'
          : 'Not compared: this amount leaves out the hospital’s own emergency room charges.'}
      </td>
    </tr>
  );
}

/** Medicare reference amounts next to a charge, with where every number comes from. */
/** Shows the given rows, or every service PatientShield has amounts for when `rows` is omitted. */
export function PriceContext({
  rows,
  title = 'Price context',
  intro,
  headingLevel = 3,
}: {
  rows?: PriceRow[];
  title?: string;
  intro?: string;
  headingLevel?: 2 | 3;
}) {
  const Heading = `h${headingLevel}` as const;
  const Sub = `h${headingLevel + 1}` as 'h3' | 'h4';
  const [state, retry] = useAsync(fetchBenchmarks);
  const [county, setCounty] = useState('');
  const headingId = useId();

  if (state.status === 'loading') {
    return (
      <p className="loading" role="status">
        <span className="spinner" aria-hidden="true" /> Loading Medicare reference amounts…
      </p>
    );
  }
  if (state.status === 'error') {
    return (
      <div className="status-card" role="status">
        <p>
          <strong>Medicare reference amounts are unavailable.</strong> {state.message}
        </p>
        <button type="button" className="btn btn-quiet" onClick={retry}>
          <Icon name="refresh" size={16} /> Try again
        </button>
      </div>
    );
  }

  const b = state.data;
  const byCode = new Map(b.rates.map((r) => [r.code, r]));
  const known = (rows ?? b.rates.map((r) => ({ key: r.code, code: r.code }))).filter((r) => byCode.has(r.code));
  const locality = localityFor(county, b);
  const c = (id: string) => b.claims[id] && <ClaimBlock key={id} claim={b.claims[id]!} />;

  return (
    <section className="price-context" aria-labelledby={headingId}>
      <Heading id={headingId} className="card-heading">
        {title}
      </Heading>
      {intro && <p className="muted">{intro}</p>}
      <p className="muted bill-disclaimer">{b.disclaimer}</p>

      <div className="mini-field">
        <label htmlFor={`${headingId}-county`}>New Jersey county where you got care</label>
        <select id={`${headingId}-county`} value={county} onChange={(e) => setCounty(e.target.value)}>
          <option value="">Not sure (show both Medicare areas)</option>
          {b.nj_counties.map((n) => (
            <option key={n} value={n}>
              {n}
            </option>
          ))}
        </select>
        <p className="field-help">Medicare pays different amounts in Northern New Jersey and the rest of the state.</p>
      </div>

      {known.length === 0 ? (
        <p>None of these services are in PatientShield’s list of {b.rates.length} common services yet.</p>
      ) : (
        // Focusable so keyboard users can scroll the table sideways on a narrow screen (axe: scrollable-region-focusable).
        // eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex
        <div className="table-scroll" role="region" aria-labelledby={`${headingId}-caption`} tabIndex={0}>
          <table className="line-table price-table">
            <caption id={`${headingId}-caption`}>Charges next to Medicare’s {b.year} amounts</caption>
            <thead>
              <tr>
                <th scope="col">Service</th>
                <th scope="col">Charge</th>
                <th scope="col">Hospital’s published price (optional)</th>
                <th scope="col">Medicare amount</th>
                <th scope="col">Comparison</th>
              </tr>
            </thead>
            <tbody>
              {known.map((r) => (
                <Row key={r.key} row={r} rate={byCode.get(r.code)!} b={b} locality={locality} />
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="price-provenance">
        Medicare amounts: CMS physician fee schedule {b.version} (file updated {formatDate(b.file_updated)}, retrieved{' '}
        {formatDate(b.retrieved)}), conversion factor ${b.conversion_factor}.
      </p>
      {c('medicare_estimate_how')}
      {c('medicare_facility_rate')}
      <Sub>Finding the hospital’s published price</Sub>
      {c('price_transparency_list')}
      {c('price_transparency_shoppable')}
      {c('price_terms')}
    </section>
  );
}
