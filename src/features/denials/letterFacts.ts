import type { Citation } from '../../core/api/documents';
import type { Extraction, ExtractedField, LetterFacts, LetterQuote, StatedDeadline } from './api';

const MAX_QUOTE = 600;

const quoteOf = (c: Citation | undefined): LetterQuote | null =>
  c ? { text: c.quote.replace(/\s+/g, ' ').trim().slice(0, MAX_QUOTE), page: c.page } : null;

function field(result: Extraction, key: ExtractedField['key']) {
  return result.fields.find((f) => f.key === key);
}

function deadlines(f: ExtractedField | undefined): StatedDeadline[] {
  if (!f || f.status !== 'found') return [];
  return f.values.flatMap((text, i) => {
    const quote = quoteOf(f.citations[i]);
    return quote ? [{ text: text.slice(0, 200), normalized: i === 0 ? f.normalized : null, quote }] : [];
  });
}

/**
 * Picks the facts the action plan needs from the extraction result: only quotes and values the letter itself contains,
 * each with its page. Nothing is inferred here.
 */
export function letterFacts(result: Extraction): LetterFacts {
  const reason = field(result, 'denial_reason');
  const instructions = field(result, 'appeal_instructions');
  const date = field(result, 'letter_date');
  const [appeal, ...others] = deadlines(field(result, 'appeal_deadline'));
  const [external] = deadlines(field(result, 'external_review_deadline'));
  return {
    letter_date: date?.status === 'found' && date.normalized && /^\d{4}-\d{2}-\d{2}$/.test(date.normalized) ? date.normalized : null,
    denial_reason: reason?.status === 'found' ? quoteOf(reason.citations[0]) : null,
    denial_statement: reason?.status === 'not_found' ? quoteOf(reason.citations[0]) : null,
    appeal_instructions: instructions?.status === 'found' ? instructions.citations.slice(0, 6).flatMap((c) => quoteOf(c) ?? []) : [],
    appeal_deadline: appeal ?? null,
    other_time_limits: others.slice(0, 6),
    external_review_deadline: external ?? null,
    urgent_mentioned: result.signals.some((s) => s.kind === 'urgent'),
  };
}
