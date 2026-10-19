import { z } from 'zod';
import { request } from '../../core/api/http';
import { ClaimOutSchema } from '../../core/api/sources';

/** The published rules. Only rules come from the server; income never goes to it. */

const Cents = z.number().int().nonnegative();

const GuidelineSchema = z.object({
  year: z.number().int(),
  region: z.string(),
  effective: z.string(),
  first_person_cents: Cents,
  additional_person_cents: Cents,
  by_household_size: z.array(Cents).length(8),
  source_ids: z.array(z.string()),
});
export type Guideline = z.infer<typeof GuidelineSchema>;

const BandSchema = z.object({ max_percent: z.number().int().positive(), patient_share_percent: z.number().int().min(0).max(100) });
export type CharityCareBand = z.infer<typeof BandSchema>;

export const RulesSchema = z.object({
  guideline: GuidelineSchema,
  charity_care_bands: z.array(BandSchema).min(1),
  charity_care_source_id: z.string(),
  uninsured_cap: z.object({ below_percent: z.number().int().positive(), medicare_percent: z.number().int().positive(), source_id: z.string() }),
  claims: z.record(z.string(), ClaimOutSchema),
  disclaimer: z.string(),
});
export type Rules = z.infer<typeof RulesSchema>;

export const fetchRules = (signal?: AbortSignal) => request('/api/uninsured/rules', RulesSchema, { signal });
