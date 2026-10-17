import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { axe } from 'vitest-axe';
import { App } from '../App';
import { checkFile, MAX_UPLOAD_BYTES } from '../lib/api';
import nj from './fixtures/extraction-nj.json';
import vague from './fixtures/extraction-vague.json';
import samples from './fixtures/samples.json';
import { jsonResponse } from './fixtures';

type Route = (url: string, init?: RequestInit) => Response | Promise<Response>;

function mockApi(extra: Record<string, Route> = {}) {
  const routes: Record<string, Route> = {
    '/api/samples': () => jsonResponse(samples),
    '/api/samples/nj-prior-auth-mri/extract': () => jsonResponse(nj),
    '/api/samples/vague-letter-missing-details/extract': () => jsonResponse(vague),
    ...extra,
  };
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = typeof input === 'string' ? input : input instanceof URL ? input.pathname : input.url;
    const route = routes[url];
    return route ? route(url, init) : jsonResponse({ error: 'not_found', message: 'Not found.' }, 404);
  });
}

function renderNavigator() {
  return render(
    <MemoryRouter initialEntries={['/navigator']}>
      <App />
    </MemoryRouter>,
  );
}

async function openSample(title: RegExp) {
  const item = (await screen.findByRole('heading', { name: title })).closest('li')!;
  await userEvent.click(within(item).getByRole('button', { name: /read this sample/i }));
  return screen.findByRole('heading', { level: 2, name: /synthetic-/ });
}

describe('Denial Navigator: sample letter → cited results', () => {
  it('lists the synthetic samples with download links', async () => {
    mockApi();
    renderNavigator();
    const item = (await screen.findByRole('heading', { name: /prior authorization denied/i })).closest('li')!;
    expect(within(item).getByRole('link', { name: /download pdf/i })).toHaveAttribute('href', '/api/samples/nj-prior-auth-mri/pdf');
  });

  it('shows extracted details, each linked to its page and passage', async () => {
    mockApi();
    renderNavigator();
    await openSample(/prior authorization denied/i);

    const reason = screen.getByRole('article', { name: /stated reason for the denial/i });
    expect(reason).toHaveTextContent(/not medically necessary/i);
    expect(within(reason).getByText('Found in letter')).toBeInTheDocument();

    const deadline = screen.getByRole('article', { name: /appeal deadline stated in the letter/i });
    const pageButton = within(deadline).getByRole('button', { name: /page 2/i });
    await userEvent.click(pageButton);
    expect(pageButton).toHaveAttribute('aria-pressed', 'true');

    const page2 = screen.getByRole('region', { name: 'Page 2' });
    const active = page2.querySelector('mark.active');
    expect(active).not.toBeNull();
    expect(active!.textContent).toContain('within 180 calendar days');
  });

  it('shows the letter text exactly, page by page, with a synthetic badge and retention notice', async () => {
    mockApi();
    renderNavigator();
    await openSample(/prior authorization denied/i);
    expect(screen.getByText('Synthetic sample')).toBeInTheDocument();
    expect(screen.getByText(/did not save it/i)).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Page 1' })).toHaveTextContent('Claim Number: CLM-2026-0915-3382');
  });

  it('says clearly when details are missing, and flags text aimed at software', async () => {
    mockApi();
    renderNavigator();
    await openSample(/vague letter/i);

    const deadline = screen.getByRole('article', { name: /appeal deadline stated in the letter/i });
    expect(within(deadline).getByText('Not in this letter')).toBeInTheDocument();
    expect(deadline).toHaveTextContent(/ask the plan for it in writing/i);

    const alerts = screen.getAllByRole('alert');
    expect(alerts.some((a) => /addressed to software/i.test(a.textContent ?? ''))).toBe(true);
    expect(document.querySelector('mark.cite-warn')?.textContent).toMatch(/ignore all previous instructions/i);
  });

  it('deletes the letter from the page on request', async () => {
    mockApi();
    renderNavigator();
    await openSample(/prior authorization denied/i);
    await userEvent.click(screen.getByRole('button', { name: /delete this letter/i }));
    expect(screen.queryByRole('region', { name: 'Page 1' })).not.toBeInTheDocument();
    expect(screen.queryByText(/CLM-2026-0915-3382/)).not.toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /upload a letter/i })).toBeInTheDocument();
  });

  it('rejects a response whose citation does not match the page text', async () => {
    const tampered = structuredClone(nj);
    tampered.fields[0]!.citations[0]!.quote = 'Your claim was approved.';
    mockApi({ '/api/samples/nj-prior-auth-mri/extract': () => jsonResponse(tampered) });
    renderNavigator();
    const item = (await screen.findByRole('heading', { name: /prior authorization denied/i })).closest('li')!;
    await userEvent.click(within(item).getByRole('button', { name: /read this sample/i }));
    expect(await screen.findByText(/unexpected format/i)).toBeInTheDocument();
    expect(screen.queryByText('Your claim was approved.')).not.toBeInTheDocument();
  });

  it('has no detectable accessibility violations on the results view', async () => {
    mockApi();
    const { container } = renderNavigator();
    await openSample(/prior authorization denied/i);
    expect(await axe(container)).toHaveNoViolations();
  });
});

describe('Denial Navigator: uploads', () => {
  const file = (name: string, content = 'Your claim was denied.', type = 'text/plain') => new File([content], name, { type });

  it('validates files in the browser before sending anything', () => {
    expect(checkFile(file('photo.png'))).toMatch(/PDF \(\.pdf\) or plain-text/);
    expect(checkFile(file('empty.txt', ''))).toMatch(/empty/);
    const big = file('big.pdf');
    Object.defineProperty(big, 'size', { value: MAX_UPLOAD_BYTES + 1 });
    expect(checkFile(big)).toMatch(/limit is 4 MB/);
    expect(checkFile(file('letter.PDF'))).toBeNull();
  });

  it('does not upload an invalid file and explains why', async () => {
    const spy = mockApi();
    renderNavigator();
    await screen.findByRole('heading', { name: /prior authorization denied/i });
    await userEvent.upload(screen.getByLabelText(/choose a file/i), file('notes.docx'), { applyAccept: false });
    expect(await screen.findByText(/choose a pdf/i)).toBeInTheDocument();
    expect(spy.mock.calls.some(([url]) => url === '/api/extract')).toBe(false);
  });

  it('sends a valid file as the raw body with its encoded name', async () => {
    let seen: RequestInit | undefined;
    mockApi({
      '/api/extract': (_url, init) => {
        seen = init;
        return jsonResponse({ ...nj, document: { ...nj.document, name: 'my letter.txt', synthetic: false, sample_id: null, kind: 'text' } });
      },
    });
    renderNavigator();
    await screen.findByRole('heading', { name: /prior authorization denied/i });
    const letter = file('my letter.txt');
    await userEvent.upload(screen.getByLabelText(/choose a file/i), letter);
    expect(await screen.findByRole('heading', { level: 2, name: 'my letter.txt' })).toBeInTheDocument();
    expect(seen?.method).toBe('POST');
    expect(seen?.body).toBe(letter);
    expect((seen?.headers as Record<string, string>)['X-File-Name']).toBe('my%20letter.txt');
  });

  it('shows the server’s explanation when a file cannot be read', async () => {
    mockApi({
      '/api/extract': () => jsonResponse({ error: 'encrypted', message: 'This PDF is password-protected. Remove the password and try again.' }, 422),
    });
    renderNavigator();
    await screen.findByRole('heading', { name: /prior authorization denied/i });
    await userEvent.upload(screen.getByLabelText(/choose a file/i), file('locked.pdf', '%PDF-1.4', 'application/pdf'));
    expect(await screen.findByRole('alert')).toHaveTextContent(/password-protected/i);
    await userEvent.click(screen.getByRole('button', { name: /try another file/i }));
    expect(screen.queryByText(/password-protected/i)).not.toBeInTheDocument();
  });
});
