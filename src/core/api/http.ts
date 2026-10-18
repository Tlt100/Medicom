import { z } from 'zod';

/**
 * Shared HTTP client. Responses are validated with zod before the UI uses them, so a broken or
 * unexpected response becomes a clear error state instead of a crash or a misleading render.
 */

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

export async function request<T>(path: string, schema: z.ZodType<T>, init: RequestInit = {}): Promise<T> {
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

export const postJson = (body: unknown, signal?: AbortSignal): RequestInit => ({
  method: 'POST',
  body: JSON.stringify(body),
  signal,
  headers: { 'Content-Type': 'application/json' },
});

export function formatDate(iso: string): string {
  const [y, m, d] = iso.split('-').map(Number);
  if (!y || !m || !d) return iso;
  return new Date(Date.UTC(y, m - 1, d)).toLocaleDateString('en-US', { timeZone: 'UTC', month: 'long', day: 'numeric', year: 'numeric' });
}
