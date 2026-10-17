import { useEffect, useMemo, useRef } from 'react';
import type { Extraction } from '../lib/api';
import { citationId, segmentText, type Span } from '../lib/highlight';

interface Props {
  result: Extraction;
  activeId: string | null;
}

/**
 * Shows the letter's text exactly as extracted, page by page, with every cited passage highlighted.
 * Text is rendered as React text nodes only, so nothing in the document can inject markup.
 */
export function DocumentViewer({ result, activeId }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  const spansByPage = useMemo(() => {
    const map = new Map<number, Span[]>();
    for (const field of result.fields) {
      field.citations.forEach((c, i) => {
        const list = map.get(c.page) ?? [];
        list.push({ id: citationId(field.key, i), start: c.start, end: c.end });
        map.set(c.page, list);
      });
    }
    result.signals
      .filter((s) => s.kind === 'suspicious')
      .forEach((s) =>
        s.citations.forEach((c, i) => {
          const list = map.get(c.page) ?? [];
          list.push({ id: citationId(`signal-${s.code}`, i), start: c.start, end: c.end });
          map.set(c.page, list);
        }),
      );
    return map;
  }, [result]);

  useEffect(() => {
    if (!activeId || !containerRef.current) return;
    // Citation ids are generated from fixed field keys ([a-z0-9_-]), so they are safe in a selector.
    const mark = containerRef.current.querySelector<HTMLElement>(`[data-cite~="${activeId}"]`);
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    mark?.scrollIntoView?.({ block: 'center', behavior: reduce ? 'auto' : 'smooth' });
  }, [activeId]);

  return (
    <div className="doc-viewer" ref={containerRef} aria-label="Your letter, with cited passages highlighted" role="region">
      {result.pages.map((page) => (
        <section key={page.number} className="doc-page" aria-label={`Page ${page.number}`} id={`doc-page-${page.number}`}>
          <p className="doc-page-label">
            Page {page.number} of {result.pages.length}
          </p>
          <div className="doc-text">
            {segmentText(page.text, spansByPage.get(page.number) ?? []).map((seg, i) =>
              seg.ids.length ? (
                <mark
                  key={i}
                  data-cite={seg.ids.join(' ')}
                  className={activeId && seg.ids.includes(activeId) ? 'cite active' : seg.ids.some((id) => id.startsWith('signal-')) ? 'cite cite-warn' : 'cite'}
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
