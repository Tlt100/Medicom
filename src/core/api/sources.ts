import { z } from 'zod';
import { request } from './http';

/** The verified source library and the plain-language claims that cite it. Shared by every feature. */

const httpsUrl = z
  .string()
  .url()
  // Rendered as a link, so only https URLs are accepted (blocks javascript:, data:, http:).
  .refine((u) => u.startsWith('https://'), 'Source links must use https');
const SourceTypeSchema = z.enum(['statute', 'regulation', 'agency-guidance', 'official-resource', 'educational']);
const ExcerptSchema = z.object({ locator: z.string(), text: z.string() });

export const SourceSchema = z.object({
  id: z.string(),
  title: z.string(),
  citation: z.string().nullable(),
  authority: z.string(),
  url: httpsUrl,
  jurisdiction: z.enum(['US-Federal', 'NJ']),
  source_type: SourceTypeSchema,
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

export const fetchRegistry = (signal?: AbortSignal) => request('/api/sources', RegistrySchema, { signal });

const ClaimSummarySchema = z.object({ id: z.string(), text: z.string(), source_ids: z.array(z.string()).min(1) });
export type ClaimSummary = z.infer<typeof ClaimSummarySchema>;
export const fetchClaims = (signal?: AbortSignal) => request('/api/claims', z.array(ClaimSummarySchema), { signal });

/** A source as it appears next to a claim (a "source library" citation). */
export const SourceRefSchema = z.object({
  id: z.string(),
  title: z.string(),
  citation: z.string().nullable(),
  authority: z.string(),
  url: httpsUrl,
  source_type: SourceTypeSchema,
  verification: z.enum(['verified', 'needs-review']),
});
export type SourceRef = z.infer<typeof SourceRefSchema>;

/** A plain-language legal statement with the sources that back it. */
export const ClaimOutSchema = z.object({ id: z.string(), text: z.string(), sources: z.array(SourceRefSchema).min(1), needs_review: z.boolean() });
export type ClaimOut = z.infer<typeof ClaimOutSchema>;

export const SOURCE_TYPE_LABEL: Record<SourceRef['source_type'], string> = {
  statute: 'Statute',
  regulation: 'Regulation',
  'agency-guidance': 'Agency guidance',
  'official-resource': 'Official resource',
  educational: 'Educational',
};
