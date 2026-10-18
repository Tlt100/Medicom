import { z } from 'zod';
import { postJson, request } from './http';
import { ClaimOutSchema, SourceRefSchema } from './sources';

/** Plan-type triage: the question tree, suggestions from document clues, and the cited result. */

const OptionSchema = z.object({ value: z.string(), label: z.string(), hint: z.string().nullable(), next: z.string().nullable() });
const QuestionSchema = z.object({ id: z.string(), prompt: z.string(), help: z.string(), options: z.array(OptionSchema).min(1) });
export type Question = z.infer<typeof QuestionSchema>;

export const FlowSchema = z
  .object({ start: z.string(), questions: z.record(z.string(), QuestionSchema) })
  .refine((f) => f.start in f.questions && Object.values(f.questions).every((q) => q.options.every((o) => !o.next || o.next in f.questions)), 'Broken flow');
export type Flow = z.infer<typeof FlowSchema>;

const SuggestionSchema = z.object({ answers: z.record(z.string(), z.string()), reasons: z.array(z.string()) });
export type Suggestion = z.infer<typeof SuggestionSchema>;

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
  claims: z.array(ClaimOutSchema),
  uncertainties: z.array(z.string()),
  how_to_confirm: z.array(z.string()),
  answers: z.array(z.object({ question: z.string(), answer: z.string() })),
});
export type TriageResult = z.infer<typeof TriageResultSchema>;

export const fetchFlow = (signal?: AbortSignal) => request('/api/triage/flow', FlowSchema, { signal });
export const fetchSuggestion = (signals: string[], signal?: AbortSignal) =>
  request('/api/triage/suggest', SuggestionSchema, postJson({ signals: signals.slice(0, 20) }, signal));
export const runTriage = (answers: Record<string, string>, signal?: AbortSignal) =>
  request('/api/triage', TriageResultSchema, postJson({ answers }, signal));
