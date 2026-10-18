import type { ClaimSummary, Source } from '../api/sources';

export const RECHECK_AFTER_DAYS = 180;

export const TOPIC_LABEL: Record<string, string> = {
  'internal-appeal': 'Internal appeals',
  'external-review': 'External review',
  'plan-type': 'Plan type',
  urgent: 'Urgent care',
  medicaid: 'Medicaid / NJ FamilyCare',
  medicare: 'Medicare',
  'denial-notice': 'Denial notices',
  complaints: 'Complaints',
};

export const WEIGHT_OPTIONS = [
  { value: 'binding', label: 'Binding law (statutes and regulations)' },
  { value: 'agency-guidance', label: 'Agency guidance' },
  { value: 'official-resource', label: 'Official resource' },
  { value: 'educational', label: 'Educational material' },
] as const;

export interface Filters {
  q: string;
  jurisdiction: '' | Source['jurisdiction'];
  weight: '' | (typeof WEIGHT_OPTIONS)[number]['value'];
  topic: string;
  status: '' | Source['verification'];
}

export const EMPTY_FILTERS: Filters = { q: '', jurisdiction: '', weight: '', topic: '', status: '' };

export const isBinding = (s: Source) => s.source_type === 'statute' || s.source_type === 'regulation';

function matchesWeight(s: Source, weight: Filters['weight']) {
  if (!weight) return true;
  return weight === 'binding' ? isBinding(s) : s.source_type === weight;
}

/** Case-insensitive search over everything a reader might type: title, citation, authority, excerpts, notes. */
function matchesQuery(s: Source, q: string, claimTexts: string[]) {
  const needle = q.trim().toLowerCase();
  if (!needle) return true;
  const haystack = [s.title, s.citation ?? '', s.authority, s.review_note ?? '', ...s.excerpts.map((e) => e.text), ...claimTexts]
    .join(' ')
    .toLowerCase();
  return needle.split(/\s+/).every((word) => haystack.includes(word));
}

export function filterSources(sources: Source[], filters: Filters, claimsBySource: Map<string, ClaimSummary[]>): Source[] {
  return sources.filter(
    (s) =>
      (!filters.jurisdiction || s.jurisdiction === filters.jurisdiction) &&
      matchesWeight(s, filters.weight) &&
      (!filters.topic || s.topics.includes(filters.topic)) &&
      (!filters.status || s.verification === filters.status) &&
      matchesQuery(
        s,
        filters.q,
        (claimsBySource.get(s.id) ?? []).map((c) => c.text),
      ),
  );
}

export function claimsBySource(claims: ClaimSummary[]): Map<string, ClaimSummary[]> {
  const map = new Map<string, ClaimSummary[]>();
  for (const c of claims) for (const id of c.source_ids) map.set(id, [...(map.get(id) ?? []), c]);
  return map;
}

/** Days since a source was last checked, using calendar dates so time zones can't shift the count. */
export function daysSinceChecked(lastChecked: string, today: Date = new Date()): number {
  const [y, m, d] = lastChecked.split('-').map(Number);
  const checked = Date.UTC(y!, m! - 1, d!);
  const now = Date.UTC(today.getFullYear(), today.getMonth(), today.getDate());
  return Math.floor((now - checked) / 86_400_000);
}

export const isDueForRecheck = (lastChecked: string, today?: Date) => daysSinceChecked(lastChecked, today) > RECHECK_AFTER_DAYS;
