import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { axe } from 'vitest-axe';
import { App } from '../App';
import { ExtractionSchema } from '../features/denials/api';
import { letterFacts } from '../features/denials/letterFacts';
import { jsonResponse } from './fixtures';
import extractionNj from './fixtures/extraction-nj.json';
import extractionVague from './fixtures/extraction-vague.json';
import flowJson from './fixtures/flow.json';
import planNj from './fixtures/plan-nj.json';
import samples from './fixtures/samples.json';
import triageNj from './fixtures/triage-nj.json';

// ---------------------------------------------------------------- letter facts

describe('letterFacts', () => {
  it('passes along only quotes and values from the letter, each with its page', () => {
    const facts = letterFacts(ExtractionSchema.parse(extractionNj));
    expect(facts.letter_date).toBe('2026-09-15');
    expect(facts.denial_reason?.page).toBe(1);
    expect(facts.denial_reason?.text).toMatch(/not medically necessary/);
    expect(facts.appeal_deadline).toMatchObject({ text: '180 calendar days of the date you receive this notice', normalized: '180 calendar days' });
    expect(facts.appeal_deadline?.quote.page).toBe(2);
    expect(facts.external_review_deadline?.text).toMatch(/^4 months/);
    expect(facts.appeal_instructions.length).toBeGreaterThan(0);
    expect(facts.urgent_mentioned).toBe(true);
  });

  it('reports a bare denial statement and missing details as null', () => {
    const facts = letterFacts(ExtractionSchema.parse(extractionVague));
    expect(facts.denial_reason).toBeNull();
    expect(facts.denial_statement?.text).toMatch(/was not approved/);
    expect(facts.appeal_deadline).toBeNull();
    expect(facts.appeal_instructions).toEqual([]);
  });
});

// ---------------------------------------------------------------- the full journey

type Route = (init?: RequestInit) => Response | Promise<Response>;

function mockApi(extra: Record<string, Route> = {}) {
  const calls: { url: string; body?: unknown }[] = [];
  const routes: Record<string, Route> = {
    '/api/samples': () => jsonResponse(samples),
    '/api/samples/nj-prior-auth-mri/extract': () => jsonResponse(extractionNj),
    '/api/triage/flow': () => jsonResponse(flowJson),
    '/api/triage/suggest': () =>
      jsonResponse({ answers: { funding: 'fully_insured', issued_state: 'nj' }, reasons: ['Your letter mentions a fully insured plan.'] }),
    '/api/triage': () => jsonResponse(triageNj),
    '/api/plan': () => jsonResponse(planNj),
    ...extra,
  };
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = typeof input === 'string' ? input : input instanceof URL ? input.pathname : input.url;
    calls.push({ url, body: init?.body && typeof init.body === 'string' ? JSON.parse(init.body) : undefined });
    const route = routes[url];
    return route ? route(init) : jsonResponse({ error: 'not_found', message: 'Not found.' }, 404);
  });
  return calls;
}

const click = (name: RegExp) => userEvent.click(screen.getByRole('button', { name }));

async function reachSituationForm() {
  render(
    <MemoryRouter initialEntries={['/navigator']}>
      <App />
    </MemoryRouter>,
  );
  const item = (await screen.findByRole('heading', { name: /prior authorization denied/i })).closest('li')!;
  await userEvent.click(within(item).getByRole('button', { name: /read this sample/i }));
  await click(/identify my plan type/i);
  await screen.findByRole('group', { name: /where does the coverage/i });
  await userEvent.click(screen.getByRole('radio', { name: /a job/i }));
  await click(/continue/i);
  await userEvent.click(screen.getByRole('radio', { name: /private company/i }));
  await click(/continue/i); // employer type
  await click(/continue/i); // funding (pre-selected from letter)
  await click(/continue/i); // issued in NJ (pre-selected from letter)
  await userEvent.click(screen.getByRole('radio', { name: /no, or it doesn’t mention it/i }));
  await click(/continue/i);
  return screen.findByRole('form', { name: /build your action plan/i });
}

describe('Action plan', () => {
  it('pre-fills the received date from the letter and says so', async () => {
    mockApi();
    await reachSituationForm();
    expect(screen.getByLabelText(/when did you receive the letter/i)).toHaveValue('2026-09-15');
    expect(screen.getByText(/filled in with the date printed on your letter \(september 15, 2026\)/i)).toBeInTheDocument();
  });

  it('sends only the plan answers, quoted letter facts and the user’s situation', async () => {
    const calls = mockApi();
    await reachSituationForm();
    const urgency = screen.getByRole('group', { name: /could waiting seriously harm your health/i });
    await userEvent.click(within(urgency).getByRole('radio', { name: 'No' }));
    await click(/show my action plan/i);
    await screen.findByRole('heading', { level: 2, name: /your action plan/i });

    const body = calls.find((c) => c.url === '/api/plan')!.body as {
      answers: Record<string, string>;
      letter: { appeal_deadline: { quote: { page: number } } };
      situation: Record<string, unknown>;
    };
    expect(Object.keys(body).sort()).toEqual(['answers', 'letter', 'situation', 'today']);
    expect(body.answers).toEqual({ coverage_source: 'job', employer_type: 'private', funding: 'fully_insured', issued_state: 'nj', grandfathered: 'no' });
    expect(body.letter.appeal_deadline.quote.page).toBe(2);
    expect(body.situation).toMatchObject({ date_received: '2026-09-15', urgent: 'no', internal_appeal: 'not_yet', final_decision_date: null });
    expect(JSON.stringify(body)).not.toMatch(/Claim Number|PBH-448210/); // identifiers aren't needed, so they aren't sent
  });

  it('shows deadlines, the letter-vs-rules comparison, a cited checklist and contacts', async () => {
    mockApi();
    await reachSituationForm();
    await click(/show my action plan/i);
    await screen.findByRole('heading', { level: 2, name: /your action plan/i });

    expect(screen.getByRole('status')).toHaveTextContent(/^plan around/i);
    const deadlines = screen.getByRole('region', { name: /deadlines/i });
    expect(within(deadlines).getByText('Stated in your letter')).toBeInTheDocument();
    expect(within(deadlines).getByText('General rule')).toBeInTheDocument();

    const row = screen.getByRole('article', { name: 'Deadline for the first appeal' });
    expect(within(row).getByText(/your letter, page 2/i)).toBeInTheDocument();
    expect(within(row).getAllByRole('link')[0]!.getAttribute('href')).toMatch(/^https:\/\//);
    expect(within(row).getByText(/at least as long as the general rule/i)).toBeInTheDocument();

    const checklist = screen.getByRole('region', { name: /checklist/i });
    const steps = within(checklist).getAllByRole('listitem').filter((li) => li.classList.contains('check-step'));
    expect(steps.length).toBe(planNj.steps.length);
    expect(within(checklist).getByRole('heading', { name: /file a written internal appeal/i })).toBeInTheDocument();
    expect(within(checklist).getAllByText('Practical step').length).toBeGreaterThan(0);

    expect(screen.getByText('1-888-393-1062')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /print or save as pdf/i })).toBeInTheDocument();
  });

  it('blocks a future received date before sending anything', async () => {
    const calls = mockApi();
    await reachSituationForm();
    const input = screen.getByLabelText(/when did you receive the letter/i);
    await userEvent.clear(input);
    await userEvent.type(input, '2099-01-01');
    await click(/show my action plan/i);
    expect(await screen.findByRole('alert')).toHaveTextContent(/can’t be in the future/i);
    expect(calls.some((c) => c.url === '/api/plan')).toBe(false);
  });

  it('shows the server’s message if the plan can’t be built, and keeps the form', async () => {
    mockApi({ '/api/plan': () => jsonResponse({ error: 'invalid_request', message: 'Some inputs were invalid.', fields: ['situation'] }, 422) });
    await reachSituationForm();
    await click(/show my action plan/i);
    expect(await screen.findByRole('alert')).toHaveTextContent(/some inputs were invalid/i);
    expect(screen.getByRole('form', { name: /build your action plan/i })).toBeInTheDocument();
  });

  it('“Edit details” returns to the form with the answers kept', async () => {
    mockApi();
    await reachSituationForm();
    const care = () => screen.getByRole('group', { name: /already received the care/i });
    await userEvent.click(within(care()).getByRole('radio', { name: 'Yes' }));
    await click(/show my action plan/i);
    await screen.findByRole('heading', { level: 2, name: /your action plan/i });
    await click(/edit details/i);
    expect(within(care()).getByRole('radio', { name: 'Yes' })).toBeChecked();
  });

  it('has no detectable accessibility violations', async () => {
    mockApi();
    await reachSituationForm();
    expect(await axe(document.body)).toHaveNoViolations();
    await click(/show my action plan/i);
    await screen.findByRole('heading', { level: 2, name: /your action plan/i });
    expect(await axe(document.body)).toHaveNoViolations();
  });
});
