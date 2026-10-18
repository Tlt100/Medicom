import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { axe } from 'vitest-axe';
import { App } from '../App';
import { jsonResponse, mockFetchJson, registryFixture } from './fixtures';

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

describe('Landing page', () => {
  it('shows the headline, prototype warning and the "What did you receive?" choices', async () => {
    mockFetchJson(registryFixture);
    renderAt('/');
    expect(screen.getByRole('heading', { level: 1, name: /denial or a medical bill/i })).toBeInTheDocument();
    expect(screen.getByRole('complementary', { name: /prototype notice/i })).toHaveTextContent(/do not upload real health information/i);
    expect(screen.getByRole('heading', { name: 'What did you receive?' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'A denial letter' })).toHaveAttribute('href', '/navigator');
    await screen.findByText('Verified against the source');
  });

  it('shows live source coverage from the API', async () => {
    mockFetchJson(registryFixture);
    renderAt('/');
    const verified = await screen.findByText('Verified against the source');
    expect(verified.nextElementSibling).toHaveTextContent('11');
    expect(screen.getByText('Flagged for human review').nextElementSibling).toHaveTextContent('1');
  });

  it('shows a clear error and recovers on retry', async () => {
    const spy = vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('offline'));
    renderAt('/');
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent(/couldn’t reach/i);

    spy.mockImplementation(async () => jsonResponse(registryFixture));
    await userEvent.click(within(alert).getByRole('button', { name: /try again/i }));
    expect(await screen.findByText('Verified against the source')).toBeInTheDocument();
  });

  it('cites the research statistic with its scope', async () => {
    mockFetchJson(registryFixture);
    renderAt('/');
    const link = screen.getByRole('link', { name: /KFF, Claims Denials and Appeals/i });
    expect(link).toHaveAttribute('href', expect.stringMatching(/^https:\/\/www\.kff\.org\//));
    expect(link).toHaveAttribute('rel', 'noopener noreferrer');
    expect(screen.getByText(/New Jersey’s state-run marketplace is not included/)).toBeInTheDocument();
    await screen.findByText('Verified against the source');
  });

  it('has no detectable accessibility violations', async () => {
    mockFetchJson(registryFixture);
    const { container } = renderAt('/');
    await screen.findByText('Verified against the source');
    expect(await axe(container)).toHaveNoViolations();
  });
});

describe('Routing', () => {
  it('renders the about page with limits and no accessibility violations', async () => {
    const { container } = renderAt('/about');
    expect(screen.getByRole('heading', { name: /what patientshield is/i })).toBeInTheDocument();
    expect(within(screen.getByRole('main')).getByText(/does not claim HIPAA compliance/i)).toBeInTheDocument();
    expect(await axe(container)).toHaveNoViolations();
  });

  it('renders a 404 for unknown routes', () => {
    renderAt('/nope');
    expect(screen.getByRole('heading', { name: /page not found/i })).toBeInTheDocument();
  });

  it('toggles the mobile menu with correct aria state', async () => {
    renderAt('/about');
    const toggle = screen.getByRole('button', { name: /open menu/i });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    await userEvent.click(toggle);
    expect(screen.getByRole('button', { name: /close menu/i })).toHaveAttribute('aria-expanded', 'true');
  });
});
