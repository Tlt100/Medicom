export interface Span {
  id: string;
  start: number;
  end: number;
}

export interface Segment {
  text: string;
  /** ids of every citation covering this segment (empty = plain text). */
  ids: string[];
}

/**
 * Splits a page's text into segments at every citation boundary so overlapping citations
 * (e.g. a sentence cited by two fields) render as nested-safe, non-overlapping pieces.
 */
export function segmentText(text: string, spans: Span[]): Segment[] {
  const valid = spans.filter((s) => s.start >= 0 && s.end <= text.length && s.end > s.start);
  const cuts = new Set<number>([0, text.length]);
  for (const s of valid) {
    cuts.add(s.start);
    cuts.add(s.end);
  }
  const points = [...cuts].sort((a, b) => a - b);
  const out: Segment[] = [];
  for (let i = 0; i < points.length - 1; i++) {
    const a = points[i]!;
    const b = points[i + 1]!;
    if (b <= a) continue;
    const ids = valid.filter((s) => s.start <= a && s.end >= b).map((s) => s.id);
    const prev = out[out.length - 1];
    if (prev && prev.ids.join() === ids.join()) prev.text += text.slice(a, b);
    else out.push({ text: text.slice(a, b), ids });
  }
  return out;
}

export const citationId = (fieldKey: string, index: number) => `${fieldKey}-${index}`;
