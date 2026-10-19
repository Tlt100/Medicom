import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { axe } from 'vitest-axe';
import { App } from '../App';
import { formatCents, parseDollars } from '../core/lib/money';
import { RulesSchema } from '../features/uninsured/api';
import { atOrBelow, below, capCents, evaluate, povertyLine, percentOfPoverty, type Answers } from '../features/uninsured/eligibility';
import { jsonResponse } from './fixtures';
import rulesJson from './fixtures/uninsured-rules.json';

const rules = RulesSchema.parse(rulesJson);
const g = rules.guideline;
const base: Answers = { resident: 'yes', coverage: 'none', njHospital: 'yes', householdSize: 1, incomeCents: 0 };
const run = (a: Partial<Answers>) => evaluate({ ...base, ...a }, rules);

// 2026 guideline for one person: $15,960. 200% = $31,920; 300% = $47,880; 500% = $79,800.
const ONE = 1_596_000;

describe('poverty guideline math', () => {
  it('uses the published table up to 8 people, then adds the increment', () => {
    expect(povertyLine(g, 1)).toBe(ONE);
    expect(povertyLine(g, 4)).toBe(3_300_000);
    expect(povertyLine(g, 8)).toBe(5_572_000);
    expect(povertyLine(g, 9)).toBe(6_140_000);
    expect(povertyLine(g, 12)).toBe(7_844_000);
    expect(() => povertyLine(g, 0)).toThrow(RangeError);
  });

  it('compares with exact integer math at the limit', () => {
    expect(atOrBelow(3_192_000, ONE, 200)).toBe(true);
    expect(atOrBelow(3_192_001, ONE, 200)).toBe(false);
    expect(below(7_980_000, ONE, 500)).toBe(false);
    expect(below(7_979_999, ONE, 500)).toBe(true);
  });

  it('shows a percentage rounded down, never up across a limit', () => {
    expect(percentOfPoverty(7_979_999, ONE)).toBe(499.9);
    expect(percentOfPoverty(7_980_000, ONE)).toBe(500);
    expect(percentOfPoverty(0, ONE)).toBe(0);
  });
});

describe('the 500% limit from the 2008 law (less than 500%)', () => {
  it('just under 500%: may be eligible', () => {
    expect(run({ incomeCents: 7_979_999 }).uninsuredCap.status).toBe('may_be_eligible');
  });

  it('exactly 500%: not covered, because the law says "less than"', () => {
    const r = run({ incomeCents: 7_980_000 }).uninsuredCap;
    expect(r.status).toBe('not_by_income');
    expect(r.headline).toMatch(/at or above 500%/);
  });

  it('just over 500%: not covered', () => {
    expect(run({ incomeCents: 7_980_001 }).uninsuredCap.status).toBe('not_by_income');
  });

  it('uses the household size: 4 people at $164,999 is under 500% of $33,000', () => {
    expect(run({ householdSize: 4, incomeCents: 16_499_999 }).uninsuredCap.status).toBe('may_be_eligible');
    expect(run({ householdSize: 4, incomeCents: 16_500_000 }).uninsuredCap.status).toBe('not_by_income');
  });

  it('does not apply to insured patients, non-residents or hospitals outside New Jersey', () => {
    expect(run({ coverage: 'partial' }).uninsuredCap.status).toBe('does_not_apply');
    expect(run({ coverage: 'full' }).uninsuredCap.status).toBe('does_not_apply');
    expect(run({ resident: 'no' }).uninsuredCap.status).toBe('does_not_apply');
    expect(run({ njHospital: 'no' }).uninsuredCap.status).toBe('does_not_apply');
  });

  it('asks the person to check when an answer is unsure, and always mentions the unconfirmed sliding scale', () => {
    const r = run({ resident: 'unsure' }).uninsuredCap;
    expect(r.status).toBe('check');
    expect(r.reasons.join(' ')).toMatch(/residency/);
    expect(run({}).uninsuredCap.reasons.join(' ')).toMatch(/sliding scale that we haven’t confirmed/);
  });
});

describe('Charity Care bands (at or below each limit)', () => {
  it.each([
    [0, 0],
    [3_192_000, 0], // exactly 200%
    [3_192_001, 20], // just over 200%
    [3_591_000, 20], // exactly 225%
    [3_591_001, 40],
    [3_990_000, 40], // exactly 250%
    [4_389_000, 60], // exactly 275%
    [4_788_000, 80], // exactly 300%
  ])('income %i cents pays %i%% of the charge', (incomeCents, share) => {
    const r = run({ incomeCents }).charityCare;
    expect(r.status).toBe('may_be_eligible');
    expect(r.patientSharePercent).toBe(share);
  });

  it('just over 300%: above the Charity Care limit', () => {
    const r = run({ incomeCents: 4_788_001 }).charityCare;
    expect(r.status).toBe('not_by_income');
    expect(r.patientSharePercent).toBeUndefined();
  });

  it('allows partial coverage but not full coverage', () => {
    expect(run({ coverage: 'partial' }).charityCare.status).toBe('may_be_eligible');
    expect(run({ coverage: 'full' }).charityCare.status).toBe('does_not_apply');
  });

  it('sends non-residents to the hospital instead of ruling them out', () => {
    const r = run({ resident: 'no' }).charityCare;
    expect(r.status).toBe('check');
    expect(r.reasons.join(' ')).toMatch(/Non-residents may qualify/);
  });

  it('always mentions assets and Medicaid screening', () => {
    expect(run({}).charityCare.reasons.join(' ')).toMatch(/assets and whether you qualify for Medicaid/);
  });
});

describe('cap math (115% of the Medicare rate)', () => {
  it.each([
    [10_000, 11_500],
    [333, 383], // 382.95 rounds to the nearest cent
    [12_345, 14_197], // 14,196.75
    [0, 0],
  ])('115%% of %i cents is %i cents', (medicare, cap) => {
    expect(capCents(medicare, 115)).toBe(cap);
  });
});

describe('dollar input', () => {
  it.each([
    ['45000', 4_500_000],
    ['$45,000', 4_500_000],
    [' 45,000.5 ', 4_500_050],
    ['0', 0],
  ])('reads %s', (input, cents) => expect(parseDollars(input)).toBe(cents));

  it.each(['', '-5', 'abc', '1.234', '1e6', '100000000001'])('rejects %s', (input) => expect(parseDollars(input)).toBeNull());

  it('formats cents', () => expect(formatCents(14_197)).toBe('$141.97'));
});

describe('wording', () => {
  it('never promises an outcome or says a bill was illegal', () => {
    const texts: string[] = [];
    for (const incomeCents of [0, 3_192_001, 4_788_001, 7_980_000]) {
      for (const coverage of ['none', 'partial', 'full', 'unsure'] as const) {
        for (const resident of ['yes', 'no', 'unsure'] as const) {
          const r = run({ incomeCents, coverage, resident });
          texts.push(r.charityCare.headline, ...r.charityCare.reasons, r.uninsuredCap.headline, ...r.uninsuredCap.reasons);
        }
      }
    }
    const all = texts.join(' ');
    expect(all).not.toMatch(/illegal|unlawful|overcharg|guarantee|you will (get|receive|qualify)|(?<!whether )you qualify\b|entitled/i);
    expect(all).toMatch(/may be eligible/);
  });
});

// ------------------------------------------------------------------ the page

function mockRules() {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
    const url = typeof input === 'string' ? input : input instanceof URL ? input.pathname : input.url;
    return url === '/api/uninsured/rules' ? jsonResponse(rulesJson) : jsonResponse({ error: 'not_found', message: 'Not found.' }, 404);
  });
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/uninsured']}>
      <App />
    </MemoryRouter>,
  );
}

async function answer({ household = '1', income = '30000', coverage = /no coverage/i } = {}) {
  await screen.findByRole('group', { name: /live in new jersey/i });
  await userEvent.click(within(screen.getByRole('group', { name: /live in new jersey/i })).getByRole('radio', { name: 'Yes' }));
  await userEvent.click(within(screen.getByRole('group', { name: /health coverage/i })).getByRole('radio', { name: coverage }));
  await userEvent.click(within(screen.getByRole('group', { name: /hospital in new jersey/i })).getByRole('radio', { name: 'Yes' }));
  await userEvent.type(screen.getByLabelText(/people in your household/i), household);
  await userEvent.type(screen.getByLabelText(/household income/i), income);
  await userEvent.click(screen.getByRole('button', { name: /see what i may be eligible for/i }));
}

describe('Uninsured page', () => {
  it('asks for every answer before estimating', async () => {
    mockRules();
    renderPage();
    await screen.findByRole('group', { name: /live in new jersey/i });
    await userEvent.click(screen.getByRole('button', { name: /see what i may be eligible for/i }));
    expect(screen.getByRole('alert')).toHaveTextContent(/answer the three questions/i);
  });

  it('rejects an income that is not a dollar amount', async () => {
    mockRules();
    renderPage();
    await answer({ income: 'lots' });
    expect(screen.getByRole('alert')).toHaveTextContent(/dollar amount/i);
  });

  it('shows both programs with their status and official sources', async () => {
    mockRules();
    renderPage();
    await answer({ income: '30000' });
    expect(await screen.findByRole('heading', { level: 2, name: /about 187.9% of the 2026 poverty guideline/i })).toBeInTheDocument();
    const charity = screen.getByRole('article', { name: 'NJ Charity Care' });
    expect(within(charity).getByText('May be eligible')).toBeInTheDocument();
    expect(charity).toHaveTextContent('the patient pays 0% of the charge');
    expect(within(charity).getAllByRole('link').map((a) => a.getAttribute('href'))).toContain(
      'https://www.nj.gov/health/hcf/documents/nj-charity-care-fact-sheet-english.pdf',
    );
    const cap = screen.getByRole('article', { name: /limit on hospital charges/i });
    expect(within(cap).getByText('May be eligible')).toBeInTheDocument();
    expect(within(cap).getAllByText('Flagged for review').length).toBeGreaterThan(0);
    expect(within(cap).getAllByRole('link').map((a) => a.getAttribute('href'))).toContain('https://pub.njleg.gov/bills/2008/PL08/60_.HTM');
  });

  it('never sends income anywhere: the only request is for the published rules', async () => {
    const spy = mockRules();
    renderPage();
    await answer({ income: '61234' });
    await screen.findByRole('heading', { level: 2, name: /poverty guideline/i });
    const urls = spy.mock.calls.map(([input]) => String(input));
    expect(urls).toEqual(['/api/uninsured/rules']);
    expect(spy.mock.calls.every(([, init]) => !init?.body)).toBe(true);
  });

  it('works out the 115% limit for a charge and says when the difference is worth asking about', async () => {
    mockRules();
    renderPage();
    await answer({ income: '60000' });
    await userEvent.type(await screen.findByLabelText(/the hospital’s charge/i), '2500');
    await userEvent.type(screen.getByLabelText(/medicare payment amount/i), '1000');
    const result = screen.getByText(/115% of \$1,000.00 is/i);
    expect(result).toHaveTextContent('$1,150.00');
    expect(result).toHaveTextContent('$1,350.00 more than that, which is worth asking the hospital about');
  });

  it('above 500% shows no calculator and says why', async () => {
    mockRules();
    renderPage();
    await answer({ income: '90000' });
    const cap = await screen.findByRole('article', { name: /limit on hospital charges/i });
    expect(within(cap).getByText('Not based on income')).toBeInTheDocument();
    expect(screen.queryByLabelText(/medicare payment amount/i)).toBeNull();
  });

  it('clears the answers on request', async () => {
    mockRules();
    renderPage();
    await answer({ income: '30000' });
    await userEvent.click(await screen.findByRole('button', { name: /clear my answers/i }));
    expect(screen.getByLabelText(/household income/i)).toHaveValue('');
    expect(screen.queryByText(/\$30,000/)).toBeNull();
  });

  it('keeps answers when changing them', async () => {
    mockRules();
    renderPage();
    await answer({ income: '30000' });
    await userEvent.click(await screen.findByRole('button', { name: /change answers/i }));
    expect(screen.getByLabelText(/household income/i)).toHaveValue('30000');
  });

  it('has no detectable accessibility violations on the questions and the results', async () => {
    mockRules();
    const { container } = renderPage();
    await screen.findByRole('group', { name: /live in new jersey/i });
    expect(await axe(container)).toHaveNoViolations();
    await answer({ income: '60000' });
    await screen.findByRole('heading', { level: 2, name: /poverty guideline/i });
    expect(await axe(container)).toHaveNoViolations();
  });
});
