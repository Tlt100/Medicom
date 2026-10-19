/** Money helpers shared by features. Amounts are whole cents so totals and percentages stay exact. */

export function formatCents(cents: number): string {
  const s = (Math.abs(cents) / 100).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return cents < 0 ? `-$${s}` : `$${s}`;
}

/** Whole dollars, for round figures such as poverty guidelines ($15,960). */
export const formatDollars = (cents: number) => `$${Math.round(cents / 100).toLocaleString('en-US')}`;

const MAX_CENTS = 100_000_000_00;

/** Parses what a person types ("$45,000", "45000.5") into cents, or null if it isn't a usable amount. */
export function parseDollars(input: string): number | null {
  const cleaned = input.trim().replace(/[$,\s]/g, '');
  if (!/^\d+(\.\d{1,2})?$/.test(cleaned)) return null;
  const [whole, frac = ''] = cleaned.split('.');
  const cents = Number(whole) * 100 + Number(frac.padEnd(2, '0'));
  return Number.isSafeInteger(cents) && cents <= MAX_CENTS ? cents : null;
}
