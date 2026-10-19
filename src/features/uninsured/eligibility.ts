import type { Guideline, Rules } from './api';

/**
 * Estimates what an uninsured New Jersey hospital patient may be eligible for. Runs only in the browser.
 *
 * Comparisons use whole cents and whole percents with integer math, so a household exactly at a limit is classified
 * by the rule's own wording: Charity Care bands are "less than or equal to"; the 2008 limit is "less than 500%".
 * Wording rule: "may be eligible", never a promise and never a finding that a bill broke the law.
 */

export type Answer = 'yes' | 'no' | 'unsure';
export type Coverage = 'none' | 'partial' | 'full' | 'unsure';

export interface Answers {
  resident: Answer;
  coverage: Coverage;
  njHospital: Answer;
  householdSize: number;
  incomeCents: number;
}

export type Status = 'may_be_eligible' | 'check' | 'not_by_income' | 'does_not_apply';

export interface ProgramResult {
  status: Status;
  headline: string;
  reasons: string[];
  /** Charity Care only: the share of the charge the patient pays in their income band. */
  patientSharePercent?: number;
}

export interface EligibilityResult {
  guidelineYear: number;
  povertyLineCents: number;
  /** Rounded down to one decimal, for display only. Eligibility uses exact comparisons. */
  percentOfPoverty: number;
  charityCare: ProgramResult;
  uninsuredCap: ProgramResult;
}

export const MAX_HOUSEHOLD = 20;

export function povertyLine(g: Guideline, size: number): number {
  if (!Number.isInteger(size) || size < 1) throw new RangeError('household size must be a whole number of at least 1');
  return size <= 8 ? g.by_household_size[size - 1]! : g.by_household_size[7]! + (size - 8) * g.additional_person_cents;
}

/** income is at or below pct% of the line. */
export const atOrBelow = (incomeCents: number, lineCents: number, pct: number) => incomeCents * 100 <= lineCents * pct;
/** income is strictly below pct% of the line. */
export const below = (incomeCents: number, lineCents: number, pct: number) => incomeCents * 100 < lineCents * pct;

export const percentOfPoverty = (incomeCents: number, lineCents: number) => Math.floor((incomeCents * 1000) / lineCents) / 10;

function charityCare(a: Answers, rules: Rules, line: number): ProgramResult {
  const bands = rules.charity_care_bands;
  const top = bands[bands.length - 1]!.max_percent;
  if (a.coverage === 'full') {
    return {
      status: 'does_not_apply',
      headline: 'Charity Care is for people without full coverage',
      reasons: ['It’s for people with no health coverage, or coverage that pays only part of the bill.'],
    };
  }
  if (a.njHospital === 'no') {
    return { status: 'does_not_apply', headline: 'Charity Care is for New Jersey hospitals', reasons: ['It covers care at acute care hospitals in New Jersey.'] };
  }
  const band = bands.find((b) => atOrBelow(a.incomeCents, line, b.max_percent));
  if (!band) {
    return {
      status: 'not_by_income',
      headline: 'Your income is above the Charity Care limit',
      reasons: [`Charity Care’s income limit is ${top}% of the poverty guideline. Based on what you entered, your household is above it.`],
    };
  }
  const reasons: string[] = [];
  if (a.resident === 'no') reasons.push('Charity Care is mainly for New Jersey residents. Non-residents may qualify under specific rules, so ask the hospital.');
  if (a.resident === 'unsure') reasons.push('You’ll need proof that you lived in New Jersey when you got care.');
  if (a.coverage === 'unsure') reasons.push('Check whether you had any coverage on the date of service.');
  if (a.njHospital === 'unsure') reasons.push('Check that the hospital is an acute care hospital in New Jersey.');
  const share =
    band.patient_share_percent === 0
      ? 'In your income band, the patient pays 0% of the charge.'
      : `In your income band, the patient pays ${band.patient_share_percent}% of the charge.`;
  return {
    status: reasons.length ? 'check' : 'may_be_eligible',
    headline: reasons.length ? 'You may be eligible for Charity Care. Check a few things first' : 'You may be eligible for Charity Care',
    reasons: [share, ...reasons, 'The hospital also checks your assets and whether you qualify for Medicaid first.'],
    patientSharePercent: band.patient_share_percent,
  };
}

function uninsuredCap(a: Answers, rules: Rules, line: number): ProgramResult {
  const { below_percent: limit, medicare_percent: pct } = rules.uninsured_cap;
  if (a.coverage === 'full' || a.coverage === 'partial') {
    return { status: 'does_not_apply', headline: 'This limit is for uninsured patients', reasons: ['The 2008 law covers patients who are uninsured.'] };
  }
  if (a.resident === 'no') {
    return { status: 'does_not_apply', headline: 'This limit is for New Jersey residents', reasons: ['The 2008 law covers uninsured residents of New Jersey.'] };
  }
  if (a.njHospital === 'no') {
    return { status: 'does_not_apply', headline: 'This limit is for New Jersey hospitals', reasons: ['The 2008 law covers hospitals licensed in New Jersey.'] };
  }
  if (!below(a.incomeCents, line, limit)) {
    return {
      status: 'not_by_income',
      headline: `Your income is at or above ${limit}% of the poverty guideline`,
      reasons: [`The 2008 law covers family gross income less than ${limit}% of the federal poverty level.`],
    };
  }
  const reasons: string[] = [];
  if (a.resident === 'unsure') reasons.push('The law covers New Jersey residents. Check your residency on the date of service.');
  if (a.coverage === 'unsure') reasons.push('The law covers uninsured patients. Check whether you had any coverage on the date of service.');
  if (a.njHospital === 'unsure') reasons.push('The law covers hospitals licensed in New Jersey. Check where you got care.');
  return {
    status: reasons.length ? 'check' : 'may_be_eligible',
    headline: reasons.length
      ? `The ${pct}% limit may apply to you. Check a few things first`
      : `You may be covered by New Jersey’s limit on hospital charges`,
    reasons: [
      `Your income is below ${limit}% of the poverty guideline, so the hospital may charge no more than ${pct}% of the Medicare rate for your care.`,
      ...reasons,
      'The law also calls for a state sliding scale that we haven’t confirmed. Ask the hospital how it applied the law to your bill.',
    ],
  };
}

export function evaluate(a: Answers, rules: Rules): EligibilityResult {
  const line = povertyLine(rules.guideline, a.householdSize);
  return {
    guidelineYear: rules.guideline.year,
    povertyLineCents: line,
    percentOfPoverty: percentOfPoverty(a.incomeCents, line),
    charityCare: charityCare(a, rules, line),
    uninsuredCap: uninsuredCap(a, rules, line),
  };
}

/** The most a covered patient may be charged: medicarePercent% of the Medicare rate, rounded to the nearest cent. */
export const capCents = (medicareCents: number, medicarePercent: number) => Math.round((medicareCents * medicarePercent) / 100);
