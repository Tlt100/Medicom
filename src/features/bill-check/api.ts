import { z } from 'zod';
import { CitationSchema, citationsMatchPages, DocumentInfoSchema, PageSchema, uploadFile } from '../../core/api/documents';
import { postJson, request } from '../../core/api/http';
import { ClaimOutSchema } from '../../core/api/sources';

/** Bill check: what was read from an EOB and a bill, and the comparison between them. Money is whole cents. */

const Cents = z.number().int();

export const ColumnKeySchema = z.enum([
  'billed',
  'allowed',
  'plan_paid',
  'deductible',
  'copay',
  'coinsurance',
  'not_covered',
  'patient_owes',
  'adjustment',
  'patient_paid',
  'balance',
]);
export type ColumnKey = z.infer<typeof ColumnKeySchema>;

export const COLUMN_LABEL: Record<ColumnKey, string> = {
  billed: 'Charge',
  allowed: 'Allowed',
  plan_paid: 'Plan paid',
  deductible: 'Deductible',
  copay: 'Copay',
  coinsurance: 'Coinsurance',
  not_covered: 'Not covered',
  patient_owes: 'You owe',
  adjustment: 'Adjustment',
  patient_paid: 'You paid',
  balance: 'Balance',
};

const LineItemSchema = z.object({
  id: z.string().regex(/^(eob|bill)-\d{1,4}$/),
  service_date: z.string().nullable(),
  code: z.string().nullable(),
  description: z.string(),
  amounts: z.partialRecord(ColumnKeySchema, Cents),
  status: z.enum(['listed', 'denied']),
  citation: CitationSchema,
});
export type LineItem = z.infer<typeof LineItemSchema>;

const TotalKeySchema = z.enum(['patient_owes', 'amount_due', 'total_charges', 'insurance_paid', 'adjustments', 'patient_paid']);

const TotalSchema = z.object({ key: TotalKeySchema, label: z.string(), amount_cents: Cents, citation: CitationSchema });
export type Total = z.infer<typeof TotalSchema>;

export const LineItemExtractionSchema = z
  .object({
    document: DocumentInfoSchema,
    pages: z.array(PageSchema),
    columns: z.array(ColumnKeySchema),
    line_items: z.array(LineItemSchema),
    totals: z.array(TotalSchema),
    warnings: z.array(z.string()),
    retention: z.string(),
  })
  // Defense in depth: never display a quoted line that doesn't match the page text it points to.
  .refine((r) => citationsMatchPages(r.pages, [...r.line_items.map((i) => i.citation), ...r.totals.map((t) => t.citation)]), 'Citation does not match page text');
export type LineItemExtraction = z.infer<typeof LineItemExtractionSchema>;

const FlagSchema = z.object({
  id: z.string(),
  kind: z.enum([
    'amount_due_exceeds_eob',
    'possible_duplicate',
    'not_on_eob',
    'charge_differs',
    'denied_on_eob',
    'on_eob_not_on_bill',
    'amount_due_below_eob',
    'no_line_items',
    'surprise_bill_context',
  ]),
  level: z.enum(['ask', 'info']),
  title: z.string(),
  detail: z.string(),
  bill_item_ids: z.array(z.string()),
  eob_item_ids: z.array(z.string()),
  claims: z.array(ClaimOutSchema),
  practical: z.boolean(),
});
export type Flag = z.infer<typeof FlagSchema>;

const MatchSchema = z.object({
  bill_item_id: z.string(),
  eob_item_id: z.string(),
  matched_on: z.array(z.enum(['date', 'code', 'charge', 'description'])),
});

export const ComparisonSchema = z.object({
  matches: z.array(MatchSchema),
  flags: z.array(FlagSchema),
  eob_patient_owes_cents: Cents.nullable(),
  bill_amount_due_cents: Cents.nullable(),
  next_steps: z.array(ClaimOutSchema),
  disclaimer: z.string(),
});
export type Comparison = z.infer<typeof ComparisonSchema>;

export interface BillCheckResult {
  eob: LineItemExtraction;
  bill: LineItemExtraction;
  comparison: Comparison;
}

const SampleResultSchema = z.object({ eob: LineItemExtractionSchema, bill: LineItemExtractionSchema, comparison: ComparisonSchema });

const SampleSchema = z.object({
  id: z.string().regex(/^[a-z0-9-]+$/),
  title: z.string(),
  description: z.string(),
  eob_filename: z.string(),
  bill_filename: z.string(),
});
export type BillCheckSample = z.infer<typeof SampleSchema>;

export const fetchBillSamples = (signal?: AbortSignal) => request('/api/bill-check/samples', z.array(SampleSchema), { signal });

export const runBillSample = (id: string, signal?: AbortSignal): Promise<BillCheckResult> =>
  request(`/api/bill-check/samples/${encodeURIComponent(id)}`, SampleResultSchema, { method: 'POST', signal });

export const billSamplePdfUrl = (id: string, doc: 'eob' | 'bill') => `/api/bill-check/samples/${encodeURIComponent(id)}/${doc}.pdf`;

/** What goes back for comparison: values only. No page text, names, or account numbers leave the browser again. */
export function comparisonInput(doc: LineItemExtraction) {
  return {
    line_items: doc.line_items.map(({ id, service_date, code, description, amounts, status }) => ({
      id,
      service_date,
      code,
      description: description.slice(0, 200),
      amounts,
      status,
    })),
    totals: doc.totals.map(({ key, amount_cents }) => ({ key, amount_cents })),
  };
}

/** Uploads an EOB and a bill through the shared pipeline, then compares them. */
export async function checkUploads(eobFile: File, billFile: File, signal?: AbortSignal): Promise<BillCheckResult> {
  const eob = await uploadFile(eobFile, 'eob', LineItemExtractionSchema, signal).catch((err: Error) => {
    throw labelled('your EOB', err);
  });
  const bill = await uploadFile(billFile, 'bill', LineItemExtractionSchema, signal).catch((err: Error) => {
    throw labelled('your bill', err);
  });
  const comparison = await request(
    '/api/bill-check/compare',
    ComparisonSchema,
    postJson({ eob: comparisonInput(eob), bill: comparisonInput(bill) }, signal),
  );
  return { eob, bill, comparison };
}

function labelled(which: string, err: Error): Error {
  if (err.name === 'AbortError') return err;
  const out = new Error(`We couldn’t read ${which}. ${err.message}`);
  out.name = err.name;
  return out;
}

export { formatCents } from '../../core/lib/money';
