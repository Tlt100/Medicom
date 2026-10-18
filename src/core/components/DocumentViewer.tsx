import { useEffect, useRef } from 'react';
import type { Page } from '../api/documents';
import { segmentText, type Span } from '../lib/highlight';

interface Props {
  pages: Page[];
  /** Cited spans for each page number. */
  spansByPage: Map<number, Span[]>;
  activeId: string | null;
  /** Citations that point at something worth caution (shown in the warning style). */
  isWarning?: (id: string) => boolean;
  label: string;
}

/**
 * Shows a document's text exactly as extracted, page by page, with every cited passage highlighted.
 * Text is rendered as React text nodes only, so nothing in the document can inject markup.
 */
export function DocumentViewer({ pages, spansByPage, activeId, isWarning = () => false, label }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!activeId || !containerRef.current) return;
    // Citation ids are generated from fixed keys ([a-z0-9_-]), so they are safe in a selector.
    const mark = containerRef.current.querySelector<HTMLElement>(`[data-cite~="${activeId}"]`);
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    mark?.scrollIntoView?.({ block: 'center', behavior: reduce ? 'auto' : 'smooth' });
  }, [activeId]);

  return (
    <div className="doc-viewer" ref={containerRef} aria-label={label} role="region">
      {pages.map((page) => (
        <section key={page.number} className="doc-page" aria-label={`Page ${page.number}`} id={`doc-page-${page.number}`}>
          <p className="doc-page-label">
            Page {page.number} of {pages.length}
          </p>
          <div className="doc-text">
            {segmentText(page.text, spansByPage.get(page.number) ?? []).map((seg, i) =>
              seg.ids.length ? (
                <mark
                  key={i}
                  data-cite={seg.ids.join(' ')}
                  className={activeId && seg.ids.includes(activeId) ? 'cite active' : seg.ids.some(isWarning) ? 'cite cite-warn' : 'cite'}
                >
                  {seg.text}
                </mark>
              ) : (
                <span key={i}>{seg.text}</span>
              ),
            )}
          </div>
        </section>
      ))}
    </div>
  );
}
