import { z } from 'zod';
import { CitationSchema, citationsMatchPages, DocumentInfoSchema, PageSchema, uploadFile } from '../../core/api/documents';
import { postJson, request } from '../../core/api/http';
import { ClaimOutSchema, SourceRefSchema } from '../../core/api/sources';
import { PlanTypeSchema } from '../../core/api/triage';

/** Denial letters: extraction results, sample letters, and the cited action plan. */

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
    document: DocumentInfoSchema,
    pages: z.array(PageSchema),
    fields: z.array(FieldSchema),
    signals: z.array(SignalSchema),
    warnings: z.array(z.string()),
    retention: z.string(),
  })
  // Defense in depth: never display a citation that doesn't match the page text it points to.
  .refine((r) => citationsMatchPages(r.pages, [...r.fields.flatMap((f) => f.citations), ...r.signals.flatMap((s) => s.citations)]), 'Citation does not match page text');
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

export const uploadDocument = (file: File, signal?: AbortSignal) => uploadFile(file, 'denial', ExtractionSchema, signal);

// ---------------------------------------------------------------- action plan

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
  // Send the user's local date so "days left" matches their calendar (the server accepts it within a day of its own).
  request('/api/plan', ActionPlanSchema, postJson({ ...body, today: new Date().toLocaleDateString('en-CA') }, signal));
