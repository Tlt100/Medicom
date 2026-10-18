import { citationId, type Span } from '../../core/lib/highlight';
import type { Extraction } from './api';

const SIGNAL_PREFIX = 'signal-';

/** Highlight spans for a denial letter: every field citation plus passages that look aimed at software. */
export function letterSpans(result: Extraction): Map<number, Span[]> {
  const map = new Map<number, Span[]>();
  const add = (page: number, span: Span) => map.set(page, [...(map.get(page) ?? []), span]);
  for (const field of result.fields) {
    field.citations.forEach((c, i) => add(c.page, { id: citationId(field.key, i), start: c.start, end: c.end }));
  }
  for (const s of result.signals.filter((sig) => sig.kind === 'suspicious')) {
    s.citations.forEach((c, i) => add(c.page, { id: citationId(`${SIGNAL_PREFIX}${s.code}`, i), start: c.start, end: c.end }));
  }
  return map;
}

export const isSignalCitation = (id: string) => id.startsWith(SIGNAL_PREFIX);
