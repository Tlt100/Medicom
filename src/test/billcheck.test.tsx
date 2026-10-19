import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { axe } from 'vitest-axe';
import { App } from '../App';
import { comparisonInput, formatCents, LineItemExtractionSchema } from '../features/bill-check/api';
import { jsonResponse } from './fixtures';
import clean from './fixtures/billcheck-clean-office-visit.json';
import er from './fixtures/billcheck-er-visit-differences.json';
import samples from './fixtures/billcheck-samples.json';

type Route = (url: string, init?: RequestInit) => Response | Promise<Response>;

function mockApi(extra: Record<string, Route> = {}) {
  const routes: Record<string, Route> = {
    '/api/bill-check/samples': () => jsonResponse(samples),
    '/api/bill-check/samples/er-visit-differences': () => jsonResponse(er),
    '/api/bill-check/samples/clean-office-visit': () => jsonResponse(clean),
    ...extra,
  };
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = typeof input === 'string' ? input : input instanceof URL ? input.pathname : input.url;
    const route = routes[url];
    return route ? route(url, init) : jsonResponse({ error: 'not_found', message: 'Not found.' }, 404);
  });
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/bill-check']}>
      <App />
    </MemoryRouter>,
  );
}

async function openSample(title: RegExp) {
  const item = (await screen.findByRole('heading', { name: title })).closest('li')!;
  await userEvent.click(within(item).getByRole('button', { name: /compare this sample/i }));
  return screen.findByRole('heading', { level: 2, name: /bill lines? match/i });
}

const section = (name: string) => screen.getByRole('heading', { level: 3, name }).parentElement!;

describe('Bill check: helpers', () => {
  it('formats cents as dollars', () => {
    expect(formatCents(251360)).toBe('$2,513.60');
    expect(formatCents(-11728)).toBe('-$117.28');
    expect(formatCents(0)).toBe('$0.00');
  });

  it('sends back values only: no page text, names or account numbers', () => {
    const sent = JSON.stringify(comparisonInput(LineItemExtractionSchema.parse(er.bill)));
    expect(sent).not.toMatch(/Riley Example|LRH-77031952|SYNTHETIC SAMPLE|citation|quote/);
    expect(JSON.parse(sent).line_items[0]).toEqual({
      id: 'bill-1',
      service_date: '2026-08-14',
      code: '99284',
      description: 'Emergency department visit',
      amounts: { billed: 198000 },
      status: 'listed',
    });
  });

  it('rejects a response whose quoted line does not match the page', () => {
    const tampered = structuredClone(er.bill);
    tampered.line_items[0]!.citation.quote = 'Amount due: $0.00';
    expect(LineItemExtractionSchema.safeParse(tampered).success).toBe(false);
  });
});

describe('Bill check: comparing a sample', () => {
  it('is reachable from "What did you receive?" and lists synthetic samples with both PDFs', async () => {
    mockApi();
    render(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>,
    );
    await userEvent.click(screen.getByRole('link', { name: 'A bill, and I have insurance' }));
    const item = (await screen.findByRole('heading', { name: /emergency visit/i })).closest('li')!;
    expect(within(item).getByRole('link', { name: 'EOB PDF' })).toHaveAttribute('href', '/api/bill-check/samples/er-visit-differences/eob.pdf');
    expect(within(item).getByRole('link', { name: 'Bill PDF' })).toHaveAttribute('href', '/api/bill-check/samples/er-visit-differences/bill.pdf');
  });

  it('shows the totals, what is worth asking about, and the cited sources', async () => {
    mockApi();
    renderPage();
    expect(await openSample(/emergency visit/i)).toHaveTextContent('3 of 4 bill lines match the EOB');
    expect(screen.getByText('The EOB says you owe').nextElementSibling).toHaveTextContent('$367.00');
    expect(screen.getByText('The bill asks for').nextElementSibling).toHaveTextContent('$409.00');
    expect(screen.getByText(/not findings that anything is wrong/i)).toBeInTheDocument();

    const ask = section('Worth asking about');
    const charge = within(ask).getByRole('article', { name: /charge for this service is different/i });
    expect(charge).toHaveTextContent('$2,250.00');
    expect(charge).toHaveTextContent('$2,100.00');
    const exceeds = within(ask).getByRole('article', { name: /asks for more than the eob says you owe/i });
    const hrefs = within(exceeds)
      .getAllByRole('link')
      .map((l) => l.getAttribute('href'));
    expect(hrefs).toContain('https://www.healthcare.gov/glossary/balance-billing/');
    expect(within(exceeds).getByText(/bill should not be higher/i)).toBeInTheDocument();
  });

  it('links each flag to the exact line on the bill and the EOB', async () => {
    mockApi();
    renderPage();
    await openSample(/emergency visit/i);
    const charge = screen.getByRole('article', { name: /charge for this service is different/i });
    const billButton = within(charge).getByRole('button', { name: /bill: ct head without contrast \(70450\)/i });
    await userEvent.click(billButton);
    expect(billButton).toHaveAttribute('aria-pressed', 'true');
    const billDoc = screen.getByRole('region', { name: /your bill, with each service line highlighted/i });
    expect(billDoc.querySelector('mark.active')?.textContent).toBe('08/14/2026 70450 CT head without contrast $2,250.00');

    await userEvent.click(within(charge).getByRole('button', { name: /eob: ct head/i }));
    const eobDoc = screen.getByRole('region', { name: /your eob, with each service line highlighted/i });
    expect(eobDoc.querySelector('mark.active')?.textContent).toContain('$2,100.00');
  });

  it('marks a denied EOB line as good to know and points to the Denial Navigator', async () => {
    mockApi();
    renderPage();
    await openSample(/emergency visit/i);
    const denied = within(section('Good to know')).getByRole('article', { name: /didn’t pay for this service/i });
    expect(within(denied).getByText('Practical suggestion')).toBeInTheDocument();
    expect(within(denied).getByRole('link', { name: /denial navigator/i })).toHaveAttribute('href', '/navigator');
  });

  it('lines up every bill line in a table with its status', async () => {
    mockApi();
    renderPage();
    await openSample(/emergency visit/i);
    const table = screen.getByRole('table', { name: /each line on the bill/i });
    const rows = within(table).getAllByRole('row').slice(1);
    expect(rows.map((r) => r.lastElementChild?.textContent)).toEqual(['Matches EOB', 'Charge differs', 'Denied on EOB', 'Not on this EOB']);
  });

  it('says plainly when nothing stands out', async () => {
    mockApi();
    renderPage();
    await openSample(/agree/i);
    expect(screen.getByText(/nothing stood out/i)).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Good to know' })).not.toBeInTheDocument();
  });

  it('deletes both documents on request', async () => {
    mockApi();
    renderPage();
    await openSample(/emergency visit/i);
    await userEvent.click(screen.getByRole('button', { name: /delete both documents/i }));
    expect(screen.queryByText(/LRH-77031952/)).not.toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /add your eob and bill/i })).toBeInTheDocument();
  });

  it('has no detectable accessibility violations on the results', async () => {
    mockApi();
    const { container } = renderPage();
    await openSample(/emergency visit/i);
    expect(await axe(container)).toHaveNoViolations();
  });
});

describe('Bill check: uploads', () => {
  const file = (name: string, content = 'x', type = 'text/plain') => new File([content], name, { type });

  it('needs both documents and checks them before sending anything', async () => {
    const spy = mockApi();
    renderPage();
    await screen.findByRole('heading', { name: /emergency visit/i });
    await userEvent.click(screen.getByRole('button', { name: /compare them/i }));
    expect(screen.getByRole('alert')).toHaveTextContent(/add both documents/i);
    await userEvent.upload(screen.getByLabelText(/explanation of benefits/i), file('eob.docx'), { applyAccept: false });
    await userEvent.upload(screen.getByLabelText(/^the bill/i), file('bill.txt'));
    await userEvent.click(screen.getByRole('button', { name: /compare them/i }));
    expect(screen.getByRole('alert')).toHaveTextContent(/your eob: choose a pdf/i);
    expect(spy.mock.calls.some(([url]) => url === '/api/extract')).toBe(false);
  });

  it('uploads each document with its type, then compares values only', async () => {
    const seen: { type?: string; body?: unknown }[] = [];
    mockApi({
      '/api/extract': (_url, init) => {
        const type = (init?.headers as Record<string, string>)['X-Document-Type'];
        seen.push({ type });
        return jsonResponse(type === 'eob' ? er.eob : er.bill);
      },
      '/api/bill-check/compare': (_url, init) => {
        seen.push({ type: 'compare', body: JSON.parse(String(init?.body)) });
        return jsonResponse(er.comparison);
      },
    });
    renderPage();
    await screen.findByRole('heading', { name: /emergency visit/i });
    await userEvent.upload(screen.getByLabelText(/explanation of benefits/i), file('eob.txt'));
    await userEvent.upload(screen.getByLabelText(/^the bill/i), file('bill.txt'));
    await userEvent.click(screen.getByRole('button', { name: /compare them/i }));
    await screen.findByRole('heading', { level: 2, name: /bill lines match/i });
    expect(seen.map((s) => s.type)).toEqual(['eob', 'bill', 'compare']);
    expect(JSON.stringify(seen[2]!.body)).not.toMatch(/quote|Riley Example/);
  });

  it('says which document could not be read', async () => {
    mockApi({
      '/api/extract': (_url, init) =>
        (init?.headers as Record<string, string>)['X-Document-Type'] === 'eob'
          ? jsonResponse(er.eob)
          : jsonResponse({ error: 'encrypted', message: 'This PDF is password-protected. Remove the password and try again.' }, 422),
    });
    renderPage();
    await screen.findByRole('heading', { name: /emergency visit/i });
    await userEvent.upload(screen.getByLabelText(/explanation of benefits/i), file('eob.txt'));
    await userEvent.upload(screen.getByLabelText(/^the bill/i), file('bill.pdf', '%PDF-1.4', 'application/pdf'));
    await userEvent.click(screen.getByRole('button', { name: /compare them/i }));
    expect(await screen.findByText(/couldn’t read your bill\. this pdf is password-protected/i)).toBeInTheDocument();
  });
});
