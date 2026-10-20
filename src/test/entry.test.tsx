import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { App } from '../App';
import { mockFetchJson } from './fixtures';

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

const chooser = () => screen.getByRole('region', { name: 'What did you receive?' });

describe('What did you receive?', () => {
  it('offers exactly the three paths, in order, each with a one-line description', () => {
    renderAt('/');
    const links = within(chooser()).getAllByRole('link');
    expect(links.map((l) => l.getAttribute('href'))).toEqual(['/navigator', '/bill-check', '/uninsured']);
    expect(links).toEqual([
      screen.getByRole('link', { name: 'A denial letter' }),
      screen.getByRole('link', { name: 'A bill, with insurance' }),
      screen.getByRole('link', { name: 'A bill, no insurance' }),
    ]);
    expect(links[1]).toHaveAccessibleDescription(/EOB/);
    expect(links[2]).toHaveAccessibleDescription(/Charity Care/);
    for (const l of links) expect((l.textContent ?? '').split(/\s+/).length).toBeLessThan(16);
  });

  it('the denial path opens the Denial Navigator', async () => {
    mockFetchJson([]);
    renderAt('/');
    await userEvent.click(screen.getByRole('link', { name: 'A denial letter' }));
    expect(await screen.findByRole('heading', { level: 1, name: /understand your denial letter/i })).toBeInTheDocument();
  });
});
