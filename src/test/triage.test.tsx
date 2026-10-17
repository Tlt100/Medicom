import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { axe } from 'vitest-axe';
import { App } from '../App';
import { FlowSchema } from '../lib/api';
import { suggestedValue, walk } from '../lib/triage';
import { jsonResponse } from './fixtures';
import extractionSelfFunded from './fixtures/extraction-selffunded.json';
import flowJson from './fixtures/flow.json';
import samples from './fixtures/samples.json';
import triageMedicaid from './fixtures/triage-medicaid.json';
import triageSelfFunded from './fixtures/triage-selffunded.json';
import triageUnknown from './fixtures/triage-unknown.json';

const flow = FlowSchema.parse(flowJson);

// ---------------------------------------------------------------- pure tree logic

describe('walk', () => {
  it('starts at the first question with no answers', () => {
    expect(walk(flow, {})).toEqual({ path: [], next: 'coverage_source', pruned: {} });
  });

  it('follows answers and reports the next question', () => {
    const r = walk(flow, { coverage_source: 'job', employer_type: 'private' });
    expect(r.path).toEqual(['coverage_source', 'employer_type']);
    expect(r.next).toBe('funding');
  });

  it('finishes at a terminal option', () => {
    expect(walk(flow, { coverage_source: 'medicaid' }).next).toBeNull();
  });

  it('drops answers that no longer apply after an earlier answer changes', () => {
    const r = walk(flow, { coverage_source: 'medicaid', employer_type: 'private', funding: 'self_funded' });
    expect(r.pruned).toEqual({ coverage_source: 'medicaid' });
  });

  it('stops at an invalid answer instead of skipping ahead', () => {
    expect(walk(flow, { coverage_source: 'bogus' }).next).toBe('coverage_source');
  });
});

describe('suggestedValue', () => {
  it('only accepts suggestions that are real options for the question', () => {
    expect(suggestedValue(flow, 'funding', { funding: 'self_funded' })).toBe('self_funded');
    expect(suggestedValue(flow, 'funding', { funding: 'approved' })).toBeUndefined();
  });
});

// ---------------------------------------------------------------- the flow in the Navigator

type Route = (init?: RequestInit) => Response | Promise<Response>;

function mockApi(extra: Record<string, Route> = {}) {
  const calls: { url: string; body?: unknown }[] = [];
  const routes: Record<string, Route> = {
    '/api/samples': () => jsonResponse(samples),
    '/api/samples/self-funded-out-of-network/extract': () => jsonResponse(extractionSelfFunded),
    '/api/triage/flow': () => jsonResponse(flowJson),
    '/api/triage/suggest': (init) => {
      const { signals } = JSON.parse(String(init?.body)) as { signals: string[] };
      return jsonResponse(
        signals.includes('self-funded')
          ? {
              answers: { coverage_source: 'job', employer_type: 'private', funding: 'self_funded' },
              reasons: ['Your letter mentions a self-funded or self-insured plan.'],
            }
          : { answers: {}, reasons: [] },
      );
    },
    '/api/triage': (init) => {
      const { answers } = JSON.parse(String(init?.body)) as { answers: Record<string, string> };
      if (answers.coverage_source === 'medicaid') return jsonResponse(triageMedicaid);
      if (answers.coverage_source === 'unsure') return jsonResponse(triageUnknown);
      return jsonResponse(triageSelfFunded);
    },
    ...extra,
  };
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = typeof input === 'string' ? input : input instanceof URL ? input.pathname : input.url;
    calls.push({ url, body: init?.body ? JSON.parse(String(init.body)) : undefined });
    const route = routes[url];
    return route ? route(init) : jsonResponse({ error: 'not_found', message: 'Not found.' }, 404);
  });
  return calls;
}

async function startTriage() {
  render(
    <MemoryRouter initialEntries={['/navigator']}>
      <App />
    </MemoryRouter>,
  );
  const item = (await screen.findByRole('heading', { name: /out-of-network claim denied/i })).closest('li')!;
  await userEvent.click(within(item).getByRole('button', { name: /read this sample/i }));
  await userEvent.click(await screen.findByRole('button', { name: /identify my plan type/i }));
  return screen.findByRole('group', { name: /where does the coverage/i });
}

const cont = () => userEvent.click(screen.getByRole('button', { name: /continue/i }));

describe('Plan-type triage', () => {
  it('pre-selects answers suggested by the letter, but the user confirms each one', async () => {
    const calls = mockApi();
    const q1 = await startTriage();
    expect(await within(q1).findByRole('radio', { name: /a job/i })).toBeChecked();
    expect(screen.getByText(/pre-selected from your letter/i)).toBeInTheDocument();
    expect(calls.some((c) => c.url === '/api/triage')).toBe(false); // nothing submitted yet

    await cont();
    expect(screen.getByRole('radio', { name: /private company/i })).toBeChecked();
    await cont();
    expect(screen.getByRole('radio', { name: /self-funded \(self-insured\)/i })).toBeChecked();
    await cont();
    await userEvent.click(screen.getByRole('radio', { name: /no, or it doesn’t mention it/i }));
    await cont();

    expect(await screen.findByRole('heading', { level: 2, name: /self-funded employer plan/i })).toBeInTheDocument();
    const sent = calls.find((c) => c.url === '/api/triage')!.body;
    expect(sent).toEqual({ answers: { coverage_source: 'job', employer_type: 'private', funding: 'self_funded', grandfathered: 'no' } });
  });

  it('shows rules with linked, labelled official sources', async () => {
    mockApi();
    await startTriage();
    for (let i = 0; i < 3; i++) await cont();
    await userEvent.click(screen.getByRole('radio', { name: /no, or it doesn’t mention it/i }));
    await cont();
    await screen.findByRole('heading', { level: 2, name: /self-funded employer plan/i });

    const rules = screen.getAllByRole('listitem').filter((li) => li.classList.contains('claim'));
    expect(rules.length).toBe(triageSelfFunded.claims.length);
    const link = within(rules[0]!).getAllByRole('link')[0]!;
    expect(link.getAttribute('href')).toMatch(/^https:\/\//);
    expect(link).toHaveAttribute('rel', 'noopener noreferrer');
    expect(within(rules[0]!).getByText(/agency guidance|regulation|educational|official resource/i)).toBeInTheDocument();
    expect(screen.getByText(/isn’t available/i)).toBeInTheDocument();
  });

  it('drops later answers when an earlier answer changes', async () => {
    const calls = mockApi();
    await startTriage();
    await cont(); // job
    await userEvent.click(screen.getByRole('button', { name: /^back$/i }));
    await userEvent.click(screen.getByRole('radio', { name: /nj familycare or medicaid/i }));
    await cont();
    expect(await screen.findByRole('heading', { level: 2, name: /nj familycare/i })).toBeInTheDocument();
    expect(calls.find((c) => c.url === '/api/triage')!.body).toEqual({ answers: { coverage_source: 'medicaid' } });
  });

  it('marks claims that rely on a source flagged for review', async () => {
    mockApi();
    await startTriage();
    await userEvent.click(screen.getByRole('radio', { name: /nj familycare or medicaid/i }));
    await cont();
    await screen.findByRole('heading', { level: 2, name: /nj familycare/i });
    expect(screen.getAllByText('Flagged for review').length).toBeGreaterThan(0);
    expect(screen.getByRole('heading', { name: /what we couldn’t confirm/i })).toBeInTheDocument();
  });

  it('“not sure” leads to how to find out, not to plan-specific deadlines', async () => {
    mockApi();
    await startTriage();
    await userEvent.click(screen.getByRole('radio', { name: /i’m not sure/i }));
    await cont();
    await screen.findByRole('heading', { level: 2, name: /plan type not yet known/i });
    expect(screen.getByText(/how to confirm your plan type/i).closest('details')).toHaveAttribute('open');
    expect(screen.queryByText(/180 days/)).not.toBeInTheDocument();
  });

  it('Back from the first question returns to the letter, and the letter can be deleted', async () => {
    mockApi();
    await startTriage();
    await userEvent.click(screen.getByRole('button', { name: /^back$/i }));
    expect(await screen.findByRole('button', { name: /delete this letter/i })).toBeInTheDocument();
  });

  it('shows the server’s message if the answers are rejected', async () => {
    mockApi({ '/api/triage': () => jsonResponse({ error: 'http_error', message: 'Missing an answer for “Which kind of Medicare is this?”' }, 422) });
    await startTriage();
    await userEvent.click(screen.getByRole('radio', { name: /nj familycare or medicaid/i }));
    await cont();
    expect(await screen.findByRole('alert')).toHaveTextContent(/missing an answer/i);
  });

  it('has no detectable accessibility violations on questions and results', async () => {
    mockApi();
    await startTriage();
    expect(await axe(document.body)).toHaveNoViolations();
    await userEvent.click(screen.getByRole('radio', { name: /nj familycare or medicaid/i }));
    await cont();
    await screen.findByRole('heading', { level: 2, name: /nj familycare/i });
    expect(await axe(document.body)).toHaveNoViolations();
  });
});
