import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { axe } from 'vitest-axe';
import { App } from '../App';

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

describe('Landing page', () => {
  it('leads with a short headline, the demo notice and the three choices', () => {
    renderAt('/');
    expect(screen.getByRole('heading', { level: 1, name: /denial or a medical bill/i })).toBeInTheDocument();
    expect(screen.getByRole('complementary', { name: /prototype notice/i })).toHaveTextContent(/not real health information/i);
    expect(screen.getByRole('heading', { name: 'What did you receive?' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'A denial letter' })).toHaveAttribute('href', '/navigator');
  });

  it('stays short: the whole page is under 120 words', () => {
    renderAt('/');
    const words = (screen.getByRole('main').textContent ?? '').split(/\s+/).filter(Boolean);
    expect(words.length).toBeLessThan(120);
  });

  it('keeps the limits one line away, with a link to the full page', () => {
    renderAt('/');
    expect(screen.getByText(/Educational, not legal advice/)).toHaveTextContent(/911/);
    expect(screen.getByRole('link', { name: /scope and limits/i })).toHaveAttribute('href', '/about');
  });

  it('has no detectable accessibility violations', async () => {
    const { container } = renderAt('/');
    expect(await axe(container)).toHaveNoViolations();
  });
});

describe('Navigation', () => {
  it('puts every tool one tap away in the header', () => {
    renderAt('/');
    const nav = screen.getByRole('navigation', { name: 'Primary' });
    expect(within(nav).getAllByRole('link').map((a) => [a.textContent, a.getAttribute('href')])).toEqual([
      ['Denial letter', '/navigator'],
      ['Bill check', '/bill-check'],
      ['No insurance', '/uninsured'],
      ['Prices', '/prices'],
      ['Sources', '/sources'],
    ]);
    expect(within(screen.getByRole('navigation', { name: 'Footer' })).getByRole('link', { name: 'About & limits' })).toHaveAttribute('href', '/about');
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
