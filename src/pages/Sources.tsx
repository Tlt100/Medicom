import { useEffect, useMemo } from 'react';
import { useLocation, useSearchParams } from 'react-router-dom';
import { Icon } from '../core/components/Icon';
import { fetchClaims, fetchRegistry, SOURCE_TYPE_LABEL, type ClaimSummary, type Registry, type Source } from '../core/api/sources';
import { formatDate } from '../core/api/http';
import {
  claimsBySource,
  filterSources,
  isBinding,
  isDueForRecheck,
  RECHECK_AFTER_DAYS,
  TOPIC_LABEL,
  WEIGHT_OPTIONS,
  type Filters,
} from '../core/lib/library';
import { useAsync } from '../core/lib/useAsync';

const load = (signal: AbortSignal) => Promise.all([fetchRegistry(signal), fetchClaims(signal)]);

const JURISDICTION_LABEL: Record<Source['jurisdiction'], string> = { 'US-Federal': 'Federal', NJ: 'New Jersey' };

function readFilters(params: URLSearchParams): Filters {
  const pick = <T extends string>(key: string, allowed: readonly T[]): T | '' => {
    const v = params.get(key) ?? '';
    return (allowed as readonly string[]).includes(v) ? (v as T) : '';
  };
  return {
    q: (params.get('q') ?? '').slice(0, 100),
    jurisdiction: pick('jurisdiction', ['US-Federal', 'NJ'] as const),
    weight: pick('weight', WEIGHT_OPTIONS.map((w) => w.value)),
    topic: pick('topic', Object.keys(TOPIC_LABEL)),
    status: pick('status', ['verified', 'needs-review'] as const),
  };
}

function SourceCard({ source, claims, highlighted }: { source: Source; claims: ClaimSummary[]; highlighted: boolean }) {
  const flagged = source.verification === 'needs-review';
  const due = isDueForRecheck(source.last_checked);
  const headingId = `source-title-${source.id}`;
  return (
    <article
      id={`source-${source.id}`}
      className={['source-card', flagged && 'source-flagged', highlighted && 'source-highlight'].filter(Boolean).join(' ')}
      aria-labelledby={headingId}
      tabIndex={-1}
    >
      <div className="source-badges">
        <span className={isBinding(source) ? 'badge badge-binding' : 'badge badge-guidance'}>{SOURCE_TYPE_LABEL[source.source_type]}</span>
        <span className="badge badge-jurisdiction">{JURISDICTION_LABEL[source.jurisdiction]}</span>
        {flagged ? <span className="badge badge-review">Flagged for review</span> : <span className="badge badge-verified">Verified</span>}
        {due && <span className="badge badge-review">Due for re-check</span>}
      </div>
      <h2 id={headingId} className="source-title">
        {source.title}
      </h2>
      {source.citation && <p className="source-citation">{source.citation}</p>}
      <p className="source-authority">{source.authority}</p>

      <dl className="source-meta">
        {source.date && source.date_label && (
          <div>
            <dt>{source.date_label}</dt>
            <dd>{formatDate(source.date)}</dd>
          </div>
        )}
        <div>
          <dt>Last checked by Medicom</dt>
          <dd>{formatDate(source.last_checked)}</dd>
        </div>
        <div>
          <dt>Topics</dt>
          <dd>{source.topics.map((t) => TOPIC_LABEL[t] ?? t).join(', ')}</dd>
        </div>
      </dl>

      {source.review_note && (
        <div className={flagged ? 'review-note flagged' : 'review-note'}>
          <p className="review-note-title">
            <Icon name="alert" size={16} /> {flagged ? 'Why this is flagged' : 'Reviewer note'}
          </p>
          <p>{source.review_note}</p>
        </div>
      )}

      {source.excerpts.length > 0 && (
        <details className="excerpts" open={highlighted}>
          <summary>
            Verbatim excerpts ({source.excerpts.length})
          </summary>
          <ul>
            {source.excerpts.map((e, i) => (
              <li key={i}>
                <blockquote>“{e.text}”</blockquote>
                <span className="excerpt-locator">{e.locator}</span>
              </li>
            ))}
          </ul>
        </details>
      )}

      <div className="used-by">
        <p className="used-by-title">Statements in Medicom that cite this source</p>
        {claims.length ? (
          <ul>
            {claims.map((c) => (
              <li key={c.id}>{c.text}</li>
            ))}
          </ul>
        ) : (
          <p className="muted">None. This source is kept to document an open question, not to support a statement.</p>
        )}
      </div>

      <a className="btn btn-secondary source-open" href={source.url} target="_blank" rel="noopener noreferrer">
        Open the official source <Icon name="external" size={16} />
        <span className="visually-hidden"> (opens in a new tab)</span>
      </a>
    </article>
  );
}

function Library({ registry, claims }: { registry: Registry; claims: ClaimSummary[] }) {
  const [params, setParams] = useSearchParams();
  const { hash } = useLocation();
  const filters = readFilters(params);
  const byId = useMemo(() => claimsBySource(claims), [claims]);
  const visible = filterSources(registry.sources, filters, byId);
  const target = hash.startsWith('#source-') ? hash.slice('#source-'.length) : null;

  // A deep link (/sources#source-<id>) scrolls to, focuses and highlights that entry.
  useEffect(() => {
    if (!target) return;
    const el = document.getElementById(`source-${target}`);
    if (!el) return;
    el.scrollIntoView?.({ block: 'start' });
    el.focus({ preventScroll: true });
  }, [target, visible.length]);

  const update = (patch: Partial<Filters>) => {
    const next = { ...filters, ...patch };
    const out = new URLSearchParams();
    (Object.keys(next) as (keyof Filters)[]).forEach((k) => next[k] && out.set(k, next[k]));
    setParams(out, { replace: true });
  };
  const active = (Object.keys(filters) as (keyof Filters)[]).some((k) => filters[k]);
  const { coverage } = registry;

  return (
    <>
      <dl className="library-stats">
        <div>
          <dt>Official sources</dt>
          <dd>{coverage.total}</dd>
        </div>
        <div>
          <dt>Verified against the source</dt>
          <dd>{coverage.verified}</dd>
        </div>
        <div>
          <dt>Flagged for review</dt>
          <dd>{coverage.needs_review}</dd>
        </div>
        <div>
          <dt>Binding regulations</dt>
          <dd>{coverage.binding}</dd>
        </div>
        <div>
          <dt>Statements citing them</dt>
          <dd>{claims.length}</dd>
        </div>
      </dl>
      <p className="muted library-reviewed">
        Library version {registry.registry_version} · last reviewed {formatDate(registry.last_reviewed)}
      </p>

      <details className="method">
        <summary>How these sources are verified</summary>
        <ul>
          <li>Each source was read on an official government website. Federal regulations come from the eCFR, with the date its text was current.</li>
          <li>Excerpts are copied word for word; Medicom’s plain-language statements cite the sources they rely on.</li>
          <li>
            Anything confirmed only secondhand, or that conflicts with another source, is <strong>flagged for review</strong> and is never
            presented as fact.
          </li>
          <li>Sources are due for a re-check {RECHECK_AFTER_DAYS} days after they were last checked.</li>
          <li>Statutes and regulations are binding law. Agency guidance, official resources and educational pages explain the law but aren’t law.</li>
        </ul>
      </details>

      <form className="filters" role="search" aria-label="Filter sources" onSubmit={(e) => e.preventDefault()}>
        <div className="filter filter-search">
          <label htmlFor="source-search">Search</label>
          <input
            id="source-search"
            type="search"
            placeholder="e.g. 180 days, IHCAP, Medicare"
            value={filters.q}
            maxLength={100}
            onChange={(e) => update({ q: e.target.value })}
          />
        </div>
        <div className="filter">
          <label htmlFor="filter-jurisdiction">Jurisdiction</label>
          <select id="filter-jurisdiction" value={filters.jurisdiction} onChange={(e) => update({ jurisdiction: e.target.value as Filters['jurisdiction'] })}>
            <option value="">All</option>
            <option value="US-Federal">Federal</option>
            <option value="NJ">New Jersey</option>
          </select>
        </div>
        <div className="filter">
          <label htmlFor="filter-weight">Legal weight</label>
          <select id="filter-weight" value={filters.weight} onChange={(e) => update({ weight: e.target.value as Filters['weight'] })}>
            <option value="">All</option>
            {WEIGHT_OPTIONS.map((w) => (
              <option key={w.value} value={w.value}>
                {w.label}
              </option>
            ))}
          </select>
        </div>
        <div className="filter">
          <label htmlFor="filter-topic">Topic</label>
          <select id="filter-topic" value={filters.topic} onChange={(e) => update({ topic: e.target.value })}>
            <option value="">All</option>
            {Object.entries(TOPIC_LABEL).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>
        <div className="filter">
          <label htmlFor="filter-status">Review status</label>
          <select id="filter-status" value={filters.status} onChange={(e) => update({ status: e.target.value as Filters['status'] })}>
            <option value="">All</option>
            <option value="verified">Verified</option>
            <option value="needs-review">Flagged for review</option>
          </select>
        </div>
      </form>

      <div className="results-bar">
        <p aria-live="polite" className="results-count">
          Showing {visible.length} of {registry.sources.length} sources
        </p>
        {active && (
          <button type="button" className="btn btn-quiet" onClick={() => setParams(new URLSearchParams(), { replace: true })}>
            Clear filters
          </button>
        )}
      </div>

      {visible.length === 0 ? (
        <div className="empty-state">
          <Icon name="doc" size={28} className="empty-icon" />
          <h2>No sources match</h2>
          <p>Try a different search word, or clear the filters to see all {registry.sources.length} sources.</p>
          <button type="button" className="btn btn-secondary" onClick={() => setParams(new URLSearchParams(), { replace: true })}>
            Clear filters
          </button>
        </div>
      ) : (
        <div className="source-list">
          {visible.map((s) => (
            <SourceCard key={s.id} source={s} claims={byId.get(s.id) ?? []} highlighted={target === s.id} />
          ))}
        </div>
      )}
    </>
  );
}

export function Sources() {
  const [state, retry] = useAsync(load);
  return (
    <div className="container page">
      <p className="eyebrow">Source library</p>
      <h1>Every source behind Medicom</h1>
      <p className="lede">The official sources behind every rule, with the exact words we rely on.</p>
      {state.status === 'loading' && (
        <div aria-busy="true" className="library-loading">
          <span className="skeleton skeleton-line" />
          <span className="skeleton skeleton-line short" />
          <span className="skeleton skeleton-line" />
          <span className="visually-hidden">Loading the source library…</span>
        </div>
      )}
      {state.status === 'error' && (
        <div className="status-card status-error" role="alert">
          <p>
            <strong>The source library couldn’t load.</strong> {state.message}
          </p>
          <button type="button" className="btn btn-quiet" onClick={retry}>
            <Icon name="refresh" size={16} /> Try again
          </button>
        </div>
      )}
      {state.status === 'ready' && <Library registry={state.data[0]} claims={state.data[1]} />}
    </div>
  );
}
