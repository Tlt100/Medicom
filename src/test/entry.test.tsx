import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { axe } from 'vitest-axe';
import { App } from '../App';
import { ENTRY_PATHS } from '../core/paths';
import { mockFetchJson, registryFixture } from './fixtures';

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

const chooser = () => screen.getByRole('region', { name: 'What did you receive?' });

describe('What did you receive?', () => {
  it('offers exactly the three paths, in order, with what each one is for', () => {
    mockFetchJson(registryFixture);
    renderAt('/');
    const links = within(chooser()).getAllByRole('link');
    expect(links.map((l) => l.getAttribute('href'))).toEqual(['/navigator', '/bill-check', '/uninsured']);
    expect(links[1]).toHaveAccessibleDescription(/Explanation of Benefits/);
    expect(links[2]).toHaveAccessibleDescription(/New Jersey hospital bills/);
  });

  it('marks every path as working, with no "Coming soon" left', () => {
    mockFetchJson(registryFixture);
    renderAt('/');
    expect(ENTRY_PATHS.every((p) => p.ready)).toBe(true);
    expect(within(chooser()).queryByText(/coming soon/i)).toBeNull();
    expect(screen.getByRole('link', { name: 'A bill, and I don’t have insurance' })).toHaveAttribute('href', '/uninsured');
  });

  it('the denial path opens the working Denial Navigator', async () => {
    mockFetchJson([]);
    renderAt('/');
    await userEvent.click(screen.getByRole('link', { name: 'A denial letter' }));
    expect(await screen.findByRole('heading', { level: 1, name: /understand your denial letter/i })).toBeInTheDocument();
  });

  it('has no detectable accessibility violations', async () => {
    mockFetchJson(registryFixture);
    const { container } = renderAt('/');
    await screen.findByText('Verified against the source');
    expect(await axe(container)).toHaveNoViolations();
  });
});
