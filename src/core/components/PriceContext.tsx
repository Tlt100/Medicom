import { useId, useState } from 'react';
import { formatDate } from '../api/http';
import { fetchBenchmarks, localityFor, timesMedicare, type Benchmarks, type BenchmarkRate } from '../api/benchmarks';
import { formatCents, parseDollars } from '../lib/money';
import { useAsync } from '../lib/useAsync';
import { Icon } from './Icon';
import { ClaimBlock, More } from './SourceLinks';

export interface PriceRow {
  key: string;
  code: string;
  /** A charge already known (from a bill). When absent, the person can type one. */
  chargeCents?: number;
}

function Amount({ cents }: { cents: number | null }) {
  return <>{cents === null ? '—' : formatCents(cents)}</>;
}

const range = (lo: string, hi: string) => (lo === hi ? lo : `${lo} to ${hi}`);

/** Above, below or about the same as Medicare, in dollars and percent. Color is backed by an arrow and words. */
function Difference({ what, cents, amounts }: { what: string; cents: number; amounts: number[] }) {
  const diffs = amounts.map((a) => cents - a);
  const pcts = amounts.map((a) => Math.round(((cents - a) * 100) / a));
  const lo = Math.min(...diffs);
  const hi = Math.max(...diffs);
  const sameAs = pcts.every((p) => Math.abs(p) < 1);
  const direction = sameAs ? 'same' : lo > 0 ? 'above' : hi < 0 ? 'below' : 'between';
  const times = amounts.map((a) => timesMedicare(cents, a));
  const [tLo, tHi] = [Math.min(...times), Math.max(...times)];
  const [pLo, pHi] = [Math.min(...pcts.map(Math.abs)), Math.max(...pcts.map(Math.abs))];
  const pct = (sign: string) => range(`${sign}${pLo}%`, `${sign}${pHi}%`);
  const dollars = range(formatCents(Math.min(Math.abs(lo), Math.abs(hi))), formatCents(Math.max(Math.abs(lo), Math.abs(hi))));

  const headline = {
    above: `${dollars} more than Medicare (${pct('+')})`,
    below: `${dollars} less than Medicare (${pct('−')})`,
    same: 'About the same as Medicare',
    between: 'Between the two Medicare amounts',
  }[direction];
  const icon = { above: '↑', below: '↓', same: '=', between: '↕' }[direction];

  return (
    <div className="price-diff-block">
      <p className="price-diff-label">{what}</p>
      <p className={`price-diff price-diff-${direction}`}>
        <span aria-hidden="true">{icon}</span> {headline}
      </p>
      <p className="price-times">
        {what} is about {range(String(tLo), String(tHi))} times the Medicare amount.
      </p>
    </div>
  );
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

  const comparable = amounts.length > 0 && amounts.every((a) => a > 0);
  const comparisons = [
    { what: 'The charge', cents: chargeCents },
    { what: 'The published price', cents: publishedCents },
  ].filter((c): c is { what: string; cents: number } => comparable && c.cents !== null);

  return (
    <tr>
      <th scope="row">
        {rate.label} <span className="muted">({rate.code})</span>
        <p className="price-covers">{rate.covers}</p>
      </th>
      <td data-label="Charge">
        {row.chargeCents !== undefined ? (
          formatCents(row.chargeCents)
        ) : (
          <input aria-label={`Charge on your bill for ${rate.label}`} inputMode="decimal" value={charge} onChange={(e) => setCharge(e.target.value)} />
        )}
      </td>
      <td data-label="Hospital’s published price (optional)">
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
      <td data-label="Medicare amount">
        {shown.map((l) => (
          <div key={l}>
            <Amount cents={rate.amounts_cents[l] ?? null} />
            {shown.length > 1 && <span className="muted"> {name(l)}</span>}
          </div>
        ))}
      </td>
      <td data-label="Comparison" aria-live="polite">
        {!rate.comparable
          ? 'Not compared: this amount leaves out the hospital’s own emergency room charges.'
          : comparisons.length
            ? comparisons.map((c) => <Difference key={c.what} what={c.what} cents={c.cents} amounts={amounts} />)
            : '—'}
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
      <p className="muted bill-disclaimer">Reference only, not what you owe.</p>
      <p className="price-why">
        <strong>You don’t need to be on Medicare to use this.</strong> Medicare’s rates are public and set by a federal formula, so
        they work as a yardstick for a price at any age, whatever insurance you have.
      </p>

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
        <p className="field-help">Northern NJ and the rest of NJ have different Medicare rates.</p>
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
      <More summary="How these numbers work">
        <p>{b.disclaimer}</p>
        <Sub>Why compare with Medicare?</Sub>
        <p>
          Medicare publishes what it pays for each service in each area, so it gives everyone the same public reference
          point. New Jersey also uses it in law:
        </p>
        {c('nj_uninsured_cap')}
        {c('medicare_estimate_how')}
        {c('medicare_facility_rate')}
        <Sub>Finding the hospital’s published price</Sub>
        {c('price_transparency_list')}
        {c('price_transparency_shoppable')}
        {c('price_terms')}
      </More>
    </section>
  );
}
