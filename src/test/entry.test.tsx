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

  it('labels unbuilt paths "Coming soon" before anyone clicks, and only those', () => {
    mockFetchJson(registryFixture);
    renderAt('/');
    expect(screen.getByRole('link', { name: 'A denial letter' })).not.toHaveTextContent(/coming soon/i);
    expect(screen.getByRole('link', { name: 'A bill, and I have insurance Coming soon' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'A bill, and I don’t have insurance Coming soon' })).toBeInTheDocument();
    const soon = ENTRY_PATHS.filter((p) => !p.ready).map((p) => p.id);
    expect(soon).toEqual(['bill-check', 'uninsured']);
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

describe.each([
  ['/bill-check', /a bill, and i have insurance/i],
  ['/uninsured', /a bill, and i don’t have insurance/i],
])('Coming-soon page %s', (path, title) => {
  it('says plainly that it is not available and offers no way to upload', async () => {
    const fetchSpy = mockFetchJson({});
    const { container } = renderAt(path);
    expect(screen.getByRole('heading', { level: 1, name: title })).toBeInTheDocument();
    expect(screen.getByRole('note', { name: /not available yet/i })).toHaveTextContent(/isn’t available yet/i);
    expect(container.querySelector('input, form, textarea')).toBeNull();
    expect(screen.queryByRole('button', { name: /upload|choose a file|check/i })).toBeNull();
    expect(fetchSpy).not.toHaveBeenCalled();
    expect(await axe(container)).toHaveNoViolations();
  });

  it('describes limits instead of promising outcomes', () => {
    mockFetchJson({});
    renderAt(path);
    const main = screen.getByRole('main');
    expect(within(main).getByRole('heading', { name: /what it won’t do/i })).toBeInTheDocument();
    expect(main).not.toHaveTextContent(/\bguaranteed\b|\bwill save\b|\byou are owed\b/i);
  });

  it('leads back to the chooser and to the working denial path', async () => {
    mockFetchJson(registryFixture);
    renderAt(path);
    expect(screen.getByRole('link', { name: /i also have a denial letter/i })).toHaveAttribute('href', '/navigator');
    await userEvent.click(screen.getByRole('link', { name: /back to “what did you receive\?”/i }));
    expect(chooser()).toBeInTheDocument();
  });
});
