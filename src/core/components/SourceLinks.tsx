import type { ReactNode } from 'react';
import { SOURCE_TYPE_LABEL, type SourceRef } from '../api/sources';
import { Icon } from './Icon';

export function SourceLink({ source }: { source: SourceRef }) {
  const binding = source.source_type === 'regulation' || source.source_type === 'statute';
  return (
    <li className="source-ref">
      <span className={binding ? 'badge badge-binding' : 'badge badge-guidance'}>{SOURCE_TYPE_LABEL[source.source_type]}</span>
      {source.verification === 'needs-review' && <span className="badge badge-review">Flagged for review</span>}
      <a href={source.url} target="_blank" rel="noopener noreferrer">
        {source.citation ?? source.title}
        <Icon name="external" size={13} />
        <span className="visually-hidden"> (opens the official source in a new tab)</span>
      </a>
      <span className="source-authority">{source.authority}</span>
      {/* New tab: the Navigator keeps the letter only in memory, so leaving the page would lose it. */}
      <a className="library-link no-print" href={`/sources#source-${source.id}`} target="_blank" rel="noopener noreferrer">
        In our library<span className="visually-hidden">: {source.title} (opens in a new tab)</span>
      </a>
    </li>
  );
}

/**
 * A plain-language rule and the official sources behind it. The rule is always visible; the source list is one tap away,
 * and its summary still names the source and says when it is flagged for review.
 */
export function ClaimBlock({ claim }: { claim: { id: string; text: string; sources: SourceRef[]; needs_review: boolean } }) {
  const [first, ...rest] = claim.sources;
  return (
    <div className={claim.needs_review ? 'claim claim-review' : 'claim'}>
      <p>{claim.text}</p>
      <details className="claim-sources">
        <summary>
          {claim.sources.length === 1 ? 'Source' : 'Sources'}: {first ? first.citation ?? first.title : 'none'}
          {rest.length > 0 && ` +${rest.length}`}
          {claim.needs_review && <span className="badge badge-review">Flagged for review</span>}
        </summary>
        <ul className="source-refs" aria-label="Sources">
          {claim.sources.map((s) => (
            <SourceLink key={s.id} source={s} />
          ))}
        </ul>
      </details>
    </div>
  );
}

/** Longer explanations, one tap away instead of up front. */
export function More({ summary, children }: { summary: string; children: ReactNode }) {
  return (
    <details className="more">
      <summary>{summary}</summary>
      <div className="more-body">{children}</div>
    </details>
  );
}
