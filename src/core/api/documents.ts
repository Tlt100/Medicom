import { z } from 'zod';
import { request } from './http';

/**
 * The document pipeline, client side: file checks before upload, the shared document and citation shapes, and a
 * generic upload. Each feature passes its own response schema. The server stores nothing; the browser holds the
 * result in memory and deletes it when the user asks.
 */

export const MAX_UPLOAD_BYTES = 4 * 1024 * 1024;
export const ACCEPTED_EXTENSIONS = ['.pdf', '.txt'];

export const DocumentTypeSchema = z.enum(['denial', 'eob', 'bill']);
export type DocumentType = z.infer<typeof DocumentTypeSchema>;

/** An exact span of the user's document. Invariant: pages[page-1].text.slice(start, end) === quote. */
export const CitationSchema = z.object({ page: z.number().int().min(1), start: z.number().int().min(0), end: z.number().int().min(0), quote: z.string() });
export type Citation = z.infer<typeof CitationSchema>;

export const PageSchema = z.object({ number: z.number().int(), text: z.string() });
export type Page = z.infer<typeof PageSchema>;

export const DocumentInfoSchema = z.object({
  name: z.string(),
  doc_type: DocumentTypeSchema,
  kind: z.enum(['pdf', 'text']),
  page_count: z.number().int(),
  size_bytes: z.number().int(),
  synthetic: z.boolean(),
  sample_id: z.string().nullable(),
});

/** True when every citation is the exact page text it points to. Used to reject a mismatched response. */
export const citationsMatchPages = (pages: Page[], citations: Citation[]) =>
  citations.every((c) => pages[c.page - 1]?.text.slice(c.start, c.end) === c.quote);

/** Checks a file before it leaves the browser. Returns a user-facing problem, or null if it looks acceptable. */
export function checkFile(file: File): string | null {
  const name = file.name.toLowerCase();
  if (!ACCEPTED_EXTENSIONS.some((ext) => name.endsWith(ext))) return 'Choose a PDF (.pdf) or plain-text (.txt) file.';
  if (file.size === 0) return 'This file is empty.';
  if (file.size > MAX_UPLOAD_BYTES) return `This file is ${(file.size / 1024 / 1024).toFixed(1)} MB. The limit is 4 MB.`;
  return null;
}

export function uploadFile<T>(file: File, docType: DocumentType, schema: z.ZodType<T>, signal?: AbortSignal) {
  return request('/api/extract', schema, {
    method: 'POST',
    body: file,
    signal,
    headers: {
      'Content-Type': file.type || 'application/octet-stream',
      'X-File-Name': encodeURIComponent(file.name.slice(0, 200)),
      'X-Document-Type': docType,
    },
  });
}
