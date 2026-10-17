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

async function getJson<T>(path: string, schema: z.ZodType<T>, signal?: AbortSignal): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, { signal, headers: { Accept: 'application/json' }, credentials: 'same-origin' });
  } catch (err) {
    if ((err as Error).name === 'AbortError') throw err;
    throw new ApiError('We couldn’t reach the PatientShield service. Check your connection and try again.');
  }
  if (!res.ok) throw new ApiError(`The service returned an error (${res.status}). Please try again shortly.`, res.status);
  let body: unknown;
  try {
    body = await res.json();
  } catch {
    throw new ApiError('The service sent a response we couldn’t read.');
  }
  const parsed = schema.safeParse(body);
  if (!parsed.success) throw new ApiError('The service sent data in an unexpected format.');
  return parsed.data;
}

export const fetchRegistry = (signal?: AbortSignal) => getJson('/api/sources', RegistrySchema, signal);

export function formatDate(iso: string): string {
  const [y, m, d] = iso.split('-').map(Number);
  if (!y || !m || !d) return iso;
  return new Date(Date.UTC(y, m - 1, d)).toLocaleDateString('en-US', { timeZone: 'UTC', month: 'long', day: 'numeric', year: 'numeric' });
}
