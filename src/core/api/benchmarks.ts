import { z } from 'zod';
import { request } from './http';
import { ClaimOutSchema } from './sources';

/** Medicare reference amounts (CMS physician fee schedule) for common services, with how they were made. */

const RateSchema = z.object({
  code: z.string().regex(/^[A-Z0-9]{5}$/),
  label: z.string(),
  category: z.string(),
  setting: z.enum(['nonfacility', 'facility']),
  covers: z.string(),
  comparable: z.boolean(),
  amounts_cents: z.record(z.string(), z.number().int().nonnegative()),
});
export type BenchmarkRate = z.infer<typeof RateSchema>;

export const BenchmarksSchema = z.object({
  year: z.number().int(),
  version: z.string(),
  file_updated: z.string(),
  retrieved: z.string(),
  conversion_factor: z.string(),
  localities: z.array(z.object({ id: z.string(), name: z.string() })).min(1),
  northern_nj_counties: z.array(z.string()),
  nj_counties: z.array(z.string()),
  rates: z.array(RateSchema),
  source_ids: z.array(z.string()),
  claims: z.record(z.string(), ClaimOutSchema),
  disclaimer: z.string(),
});
export type Benchmarks = z.infer<typeof BenchmarksSchema>;

export const fetchBenchmarks = (signal?: AbortSignal) => request('/api/benchmarks', BenchmarksSchema, { signal });

/** Medicare locality for a New Jersey county ("01" Northern NJ, "99" rest of NJ), or null when not chosen. */
export function localityFor(county: string, b: Benchmarks): string | null {
  if (!county) return null;
  return b.northern_nj_counties.includes(county) ? '01' : '99';
}

/** How many times the Medicare amount a charge is, to one decimal. */
export const timesMedicare = (chargeCents: number, medicareCents: number) => Math.round((chargeCents * 10) / medicareCents) / 10;
