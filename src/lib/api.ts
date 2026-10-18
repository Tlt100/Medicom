import { z } from 'zod';

/**
 * Typed API client. Responses are validated with zod before the UI uses them, so a broken or
 * unexpected response becomes a clear error state instead of a crash or a misleading render.
 */

const ExcerptSchema = z.object({ locator: z.string(), text: z.string() });

export const SourceSchema = z.object({
  id: z.string(),
  title: z.string(),
  citation: z.string().nullable(),
  authority: z.string(),
  // Rendered as a link, so only https URLs are accepted (blocks javascript:, data:, http:).
  url: z.string().url().refine((u) => u.startsWith('https://'), 'Source links must use https'),
  jurisdiction: z.enum(['US-Federal', 'NJ']),
  source_type: z.enum(['statute', 'regulation', 'agency-guidance', 'official-resource', 'educational']),
  topics: z.array(z.string()),
  date: z.string().nullable(),
  date_label: z.string().nullable(),
  last_checked: z.string(),
  excerpts: z.array(ExcerptSchema),
  verification: z.enum(['verified', 'needs-review']),
  review_note: z.string().nullable(),
  version: z.number(),
});
export type Source = z.infer<typeof SourceSchema>;

export const RegistrySchema = z.object({
  registry_version: z.number(),
  last_reviewed: z.string(),
  coverage: z.object({
    total: z.number(),
    verified: z.number(),
    needs_review: z.number(),
    binding: z.number(),
    federal: z.number(),
    nj: z.number(),
  }),
  sources: z.array(SourceSchema),
});
export type Registry = z.infer<typeof RegistrySchema>;

export class ApiError extends Error {
  constructor(
    message: string,
    public status?: number,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

const ErrorBodySchema = z.object({ error: z.string(), message: z.string().max(400) });

async function request<T>(path: string, schema: z.ZodType<T>, init: RequestInit = {}): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, { credentials: 'same-origin', ...init, headers: { Accept: 'application/json', ...init.headers } });
  } catch (err) {
    if ((err as Error).name === 'AbortError') throw err;
    throw new ApiError('We couldn’t reach the PatientShield service. Check your connection and try again.');
  }
  let body: unknown;
  try {
    body = await res.json();
  } catch {
    body = undefined;
  }
  if (!res.ok) {
    // The server's error messages are fixed, user-facing strings; show them when present.
    const err = ErrorBodySchema.safeParse(body);
    if (err.success) throw new ApiError(err.data.message, res.status);
    // Vercel rejects bodies over 4.5 MB itself, with a plain-text page, before the app sees them.
    if (res.status === 413) throw new ApiError('This file is too large. The limit is 4 MB.', 413);
    throw new ApiError(`The service returned an error (${res.status}). Please try again shortly.`, res.status);
  }
  if (body === undefined) throw new ApiError('The service sent a response we couldn’t read.');
  const parsed = schema.safeParse(body);
  if (!parsed.success) throw new ApiError('The service sent data in an unexpected format.');
  return parsed.data;
}

export const fetchRegistry = (signal?: AbortSignal) => request('/api/sources', RegistrySchema, { signal });

// ---------------------------------------------------------------- documents & extraction

export const MAX_UPLOAD_BYTES = 4 * 1024 * 1024;
export const ACCEPTED_EXTENSIONS = ['.pdf', '.txt'];

const CitationSchema = z.object({ page: z.number().int().min(1), start: z.number().int().min(0), end: z.number().int().min(0), quote: z.string() });
export type Citation = z.infer<typeof CitationSchema>;

export const FieldKeySchema = z.enum([
  'denial_reason',
  'appeal_instructions',
  'appeal_deadline',
  'external_review_deadline',
  'letter_date',
  'insurer_name',
  'plan_name',
  'reference_numbers',
]);
export type FieldKey = z.infer<typeof FieldKeySchema>;

const FieldSchema = z.object({
  key: FieldKeySchema,
  label: z.string(),
  status: z.enum(['found', 'not_found']),
  value: z.string().nullable(),
  values: z.array(z.string()),
  normalized: z.string().nullable(),
  citations: z.array(CitationSchema),
  confidence: z.enum(['high', 'medium']).nullable(),
  note: z.string().nullable(),
});
export type ExtractedField = z.infer<typeof FieldSchema>;

const SignalSchema = z.object({
  kind: z.enum(['plan-type', 'urgent', 'suspicious']),
  code: z.string(),
  label: z.string(),
  citations: z.array(CitationSchema),
});
export type Signal = z.infer<typeof SignalSchema>;

export const ExtractionSchema = z
  .object({
    document: z.object({
      name: z.string(),
      kind: z.enum(['pdf', 'text']),
      page_count: z.number().int(),
      size_bytes: z.number().int(),
      synthetic: z.boolean(),
      sample_id: z.string().nullable(),
    }),
    pages: z.array(z.object({ number: z.number().int(), text: z.string() })),
    fields: z.array(FieldSchema),
    signals: z.array(SignalSchema),
    warnings: z.array(z.string()),
    retention: z.string(),
  })
  // Defense in depth: never display a citation that doesn't match the page text it points to.
  .refine(
    (r) =>
      [...r.fields.flatMap((f) => f.citations), ...r.signals.flatMap((s) => s.citations)].every(
        (c) => r.pages[c.page - 1]?.text.slice(c.start, c.end) === c.quote,
      ),
    'Citation does not match page text',
  );
export type Extraction = z.infer<typeof ExtractionSchema>;

const SampleSchema = z.object({
  id: z.string().regex(/^[a-z0-9-]+$/),
  title: z.string(),
  description: z.string(),
  scenario: z.string(),
  filename: z.string(),
  page_count: z.number().int(),
});
export type Sample = z.infer<typeof SampleSchema>;

export const fetchSamples = (signal?: AbortSignal) => request('/api/samples', z.array(SampleSchema), { signal });

export const extractSample = (id: string, signal?: AbortSignal) =>
  request(`/api/samples/${encodeURIComponent(id)}/extract`, ExtractionSchema, { method: 'POST', signal });

export const samplePdfUrl = (id: string) => `/api/samples/${encodeURIComponent(id)}/pdf`;

/** Checks a file before it leaves the browser. Returns a user-facing problem, or null if it looks acceptable. */
export function checkFile(file: File): string | null {
  const name = file.name.toLowerCase();
  if (!ACCEPTED_EXTENSIONS.some((ext) => name.endsWith(ext))) return 'Choose a PDF (.pdf) or plain-text (.txt) file.';
  if (file.size === 0) return 'This file is empty.';
  if (file.size > MAX_UPLOAD_BYTES) return `This file is ${(file.size / 1024 / 1024).toFixed(1)} MB. The limit is 4 MB.`;
  return null;
}

export function uploadDocument(file: File, signal?: AbortSignal) {
  return request('/api/extract', ExtractionSchema, {
    method: 'POST',
    body: file,
    signal,
    headers: {
      'Content-Type': file.type || 'application/octet-stream',
      'X-File-Name': encodeURIComponent(file.name.slice(0, 200)),
    },
  });
}

// ---------------------------------------------------------------- plan-type triage

const OptionSchema = z.object({ value: z.string(), label: z.string(), hint: z.string().nullable(), next: z.string().nullable() });
const QuestionSchema = z.object({ id: z.string(), prompt: z.string(), help: z.string(), options: z.array(OptionSchema).min(1) });
export type Question = z.infer<typeof QuestionSchema>;

export const FlowSchema = z
  .object({ start: z.string(), questions: z.record(z.string(), QuestionSchema) })
  .refine((f) => f.start in f.questions && Object.values(f.questions).every((q) => q.options.every((o) => !o.next || o.next in f.questions)), 'Broken flow');
export type Flow = z.infer<typeof FlowSchema>;

const SuggestionSchema = z.object({ answers: z.record(z.string(), z.string()), reasons: z.array(z.string()) });
export type Suggestion = z.infer<typeof SuggestionSchema>;

const SourceRefSchema = z.object({
  id: z.string(),
  title: z.string(),
  citation: z.string().nullable(),
  authority: z.string(),
  url: z.string().url().refine((u) => u.startsWith('https://'), 'Source links must use https'),
  source_type: z.enum(['statute', 'regulation', 'agency-guidance', 'official-resource', 'educational']),
  verification: z.enum(['verified', 'needs-review']),
});
export type SourceRef = z.infer<typeof SourceRefSchema>;

export const PlanTypeSchema = z.enum([
  'nj-regulated',
  'marketplace',
  'self-funded',
  'medicaid',
  'medicare',
  'other-state',
  'government-or-religious',
  'unknown',
]);

export const TriageResultSchema = z.object({
  plan_type: PlanTypeSchema,
  label: z.string(),
  confidence: z.enum(['confirmed', 'needs-confirmation']),
  summary: z.string(),
  regulator: z.object({ name: z.string(), source: SourceRefSchema.nullable() }).nullable(),
  claims: z.array(z.object({ id: z.string(), text: z.string(), sources: z.array(SourceRefSchema).min(1), needs_review: z.boolean() })),
  uncertainties: z.array(z.string()),
  how_to_confirm: z.array(z.string()),
  answers: z.array(z.object({ question: z.string(), answer: z.string() })),
});
export type TriageResult = z.infer<typeof TriageResultSchema>;

const json = (body: unknown, signal?: AbortSignal): RequestInit => ({
  method: 'POST',
  body: JSON.stringify(body),
  signal,
  headers: { 'Content-Type': 'application/json' },
});

export const fetchFlow = (signal?: AbortSignal) => request('/api/triage/flow', FlowSchema, { signal });
export const fetchSuggestion = (signals: string[], signal?: AbortSignal) =>
  request('/api/triage/suggest', SuggestionSchema, json({ signals: signals.slice(0, 20) }, signal));
export const runTriage = (answers: Record<string, string>, signal?: AbortSignal) =>
  request('/api/triage', TriageResultSchema, json({ answers }, signal));

// ---------------------------------------------------------------- action plan

const ClaimOutSchema = z.object({ id: z.string(), text: z.string(), sources: z.array(SourceRefSchema).min(1), needs_review: z.boolean() });
const LetterQuoteSchema = z.object({ text: z.string(), page: z.number().int().min(1) });
const isoDate = z.string().regex(/^\d{4}-\d{2}-\d{2}$/);

export const ActionPlanSchema = z.object({
  plan_type: PlanTypeSchema,
  label: z.string(),
  today: isoDate,
  comparisons: z.array(
    z.object({
      topic: z.string(),
      letter: LetterQuoteSchema.nullable(),
      letter_status: z.enum(['found', 'not_found']),
      letter_summary: z.string(),
      rules: z.array(ClaimOutSchema),
      rules_summary: z.string().nullable(),
      note: z.string().nullable(),
    }),
  ),
  deadlines: z.array(
    z.object({
      id: z.string(),
      label: z.string(),
      date: isoDate,
      basis: z.string(),
      kind: z.enum(['letter', 'rule']),
      claim: ClaimOutSchema.nullable(),
      quote: LetterQuoteSchema.nullable(),
      days_left: z.number().int(),
      passed: z.boolean(),
      note: z.string().nullable(),
    }),
  ),
  plan_around: z.string().nullable(),
  steps: z.array(
    z.object({
      id: z.string(),
      title: z.string(),
      detail: z.string(),
      kind: z.enum(['rule', 'practical', 'letter', 'urgent']),
      due: isoDate.nullable(),
      claims: z.array(ClaimOutSchema),
      quote: LetterQuoteSchema.nullable(),
    }),
  ),
  documents: z.array(z.string()),
  questions: z.array(z.string()),
  contacts: z.array(
    z.object({ name: z.string(), when: z.string(), phone: z.string().nullable(), source: SourceRefSchema, claim: ClaimOutSchema.nullable() }),
  ),
  uncertainties: z.array(z.string()),
  disclaimer: z.string(),
});
export type ActionPlan = z.infer<typeof ActionPlanSchema>;

export interface Situation {
  date_received: string | null;
  care_received: 'yes' | 'no' | 'unsure';
  internal_appeal: 'not_yet' | 'waiting' | 'decided';
  final_decision_date: string | null;
  urgent: 'yes' | 'no' | 'unsure';
}

export interface LetterQuote {
  text: string;
  page: number;
}
export interface StatedDeadline {
  text: string;
  normalized: string | null;
  quote: LetterQuote;
}
export interface LetterFacts {
  letter_date: string | null;
  denial_reason: LetterQuote | null;
  denial_statement: LetterQuote | null;
  appeal_instructions: LetterQuote[];
  appeal_deadline: StatedDeadline | null;
  other_time_limits: StatedDeadline[];
  external_review_deadline: StatedDeadline | null;
  urgent_mentioned: boolean;
}

export const buildPlan = (body: { answers: Record<string, string>; letter: LetterFacts; situation: Situation }, signal?: AbortSignal) =>
  request('/api/plan', ActionPlanSchema, json(body, signal));

export const SOURCE_TYPE_LABEL: Record<SourceRef['source_type'], string> = {
  statute: 'Statute',
  regulation: 'Regulation',
  'agency-guidance': 'Agency guidance',
  'official-resource': 'Official resource',
  educational: 'Educational',
};

export function formatDate(iso: string): string {
  const [y, m, d] = iso.split('-').map(Number);
  if (!y || !m || !d) return iso;
  return new Date(Date.UTC(y, m - 1, d)).toLocaleDateString('en-US', { timeZone: 'UTC', month: 'long', day: 'numeric', year: 'numeric' });
}
