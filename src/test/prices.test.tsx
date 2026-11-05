import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { axe } from 'vitest-axe';
import { App } from '../App';
import { BenchmarksSchema, localityFor, timesMedicare } from '../core/api/benchmarks';
import { jsonResponse } from './fixtures';
import benchmarksJson from './fixtures/benchmarks.json';

const b = BenchmarksSchema.parse(benchmarksJson);

function mockApi() {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
    const url = typeof input === 'string' ? input : input instanceof URL ? input.pathname : input.url;
    return url === '/api/benchmarks' ? jsonResponse(benchmarksJson) : jsonResponse({ error: 'not_found', message: 'Not found.' }, 404);
  });
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/prices']}>
      <App />
    </MemoryRouter>,
  );
}

const rowFor = (code: string) => screen.getByRole('rowheader', { name: new RegExp(`\\(${code}\\)`) }).closest('tr')!;

describe('benchmark helpers', () => {
  it('maps counties to Medicare localities from CMS’s list', () => {
    expect(localityFor('Bergen', b)).toBe('01');
    expect(localityFor('Warren', b)).toBe('01');
    expect(localityFor('Mercer', b)).toBe('99');
    expect(localityFor('Cape May', b)).toBe('99');
    expect(localityFor('', b)).toBeNull();
    expect(b.nj_counties).toHaveLength(21);
  });

  it('expresses a charge as a multiple of the Medicare amount, to one decimal', () => {
    expect(timesMedicare(145_000, 20_688)).toBe(7);
    expect(timesMedicare(21_000, 15_065)).toBe(1.4);
    expect(timesMedicare(15_065, 15_065)).toBe(1);
  });
});

describe('Price context page', () => {
  it('lists every service with both New Jersey Medicare amounts and where they come from', async () => {
    mockApi();
    renderPage();
    await screen.findByRole('table', { name: /medicare’s 2026 amounts/i });
    expect(screen.getAllByRole('row')).toHaveLength(b.rates.length + 1);
    const mri = rowFor('72148');
    expect(mri).toHaveTextContent('$217.42');
    expect(mri).toHaveTextContent('$206.88');
    expect(mri).toHaveTextContent(/including the reading/i);
    expect(screen.getByText(/RVU26D \(file updated August 26, 2026, retrieved October 19, 2026\), conversion factor \$33\.4009/)).toBeInTheDocument();
    const links = screen.getAllByRole('link').map((a) => a.getAttribute('href'));
    expect(links).toContain('https://www.cms.gov/medicare/payment/fee-schedules/physician/pfs-relative-value-files/rvu26d');
    expect(links).toContain('https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-E/part-180');
  });

  it('narrows to one Medicare area when the county is chosen', async () => {
    mockApi();
    renderPage();
    await screen.findByRole('table');
    await userEvent.selectOptions(screen.getByLabelText(/county where you got care/i), 'Mercer');
    const mri = rowFor('72148');
    expect(mri).toHaveTextContent('$206.88');
    expect(mri).not.toHaveTextContent('$217.42');
  });

  it('compares a typed charge and a published price with the Medicare amount', async () => {
    mockApi();
    renderPage();
    await screen.findByRole('table');
    await userEvent.selectOptions(screen.getByLabelText(/county where you got care/i), 'Mercer');
    const mri = rowFor('72148');
    await userEvent.type(within(mri).getByLabelText(/charge on your bill/i), '1450');
    await userEvent.type(within(mri).getByLabelText(/published price/i), '620');
    expect(mri).toHaveTextContent('The charge is about 7 times the Medicare amount.');
    expect(mri).toHaveTextContent('The published price is about 3 times the Medicare amount.');
  });

  it('says how much more or less than Medicare a price is, in dollars and percent', async () => {
    mockApi();
    renderPage();
    await screen.findByRole('table');
    await userEvent.selectOptions(screen.getByLabelText(/county where you got care/i), 'Mercer');
    const mri = rowFor('72148');
    await userEvent.type(within(mri).getByLabelText(/charge on your bill/i), '1450');
    await userEvent.type(within(mri).getByLabelText(/published price/i), '150');
    const above = within(mri).getByText(/more than Medicare/);
    expect(above).toHaveTextContent('$1,243.12 more than Medicare (+601%)');
    expect(above).toHaveClass('price-diff-above');
    const below = within(mri).getByText(/less than Medicare/);
    expect(below).toHaveTextContent('$56.88 less than Medicare (−27%)');
    expect(below).toHaveClass('price-diff-below');
  });

  it('shows a range, or says so, when the county is not chosen', async () => {
    mockApi();
    renderPage();
    await screen.findByRole('table');
    const visit = rowFor('99203');
    await userEvent.type(within(visit).getByLabelText(/charge on your bill/i), '128');
    expect(within(visit).getByText(/between the two medicare amounts/i)).toHaveClass('price-diff-between');
    await userEvent.clear(within(visit).getByLabelText(/charge on your bill/i));
    await userEvent.type(within(visit).getByLabelText(/charge on your bill/i), '100');
    expect(within(visit).getByText(/less than Medicare/)).toHaveTextContent(/\$25\.64 to \$30\.71 less than Medicare \(−20% to −23%\)/);
  });

  it('explains that Medicare is a yardstick for anyone, not only people on Medicare', async () => {
    mockApi();
    renderPage();
    await screen.findByRole('table');
    expect(screen.getByRole('main')).toHaveTextContent(/don’t need to be on Medicare/);
  });

  it('does not compare an emergency visit charge with a doctor’s fee', async () => {
    mockApi();
    renderPage();
    await screen.findByRole('table');
    const er = rowFor('99284');
    await userEvent.type(within(er).getByLabelText(/charge on your bill/i), '1980');
    expect(er).toHaveTextContent(/not compared/i);
    expect(er).not.toHaveTextContent(/times the Medicare amount/);
  });

  it('frames the numbers as context, never as proof of a problem', async () => {
    mockApi();
    renderPage();
    await screen.findByRole('table');
    const main = screen.getByRole('main');
    expect(main).toHaveTextContent(/not what you owe/);
    expect(main).not.toHaveTextContent(/overcharg|illegal|rip-?off|gouging|fair price/i);
  });

  it('is in the main navigation', async () => {
    mockApi();
    renderPage();
    expect(screen.getAllByRole('link', { name: 'Prices' })[0]).toHaveAttribute('href', '/prices');
  });

  it('has no detectable accessibility violations', async () => {
    mockApi();
    const { container } = renderPage();
    await screen.findByRole('table');
    expect(await axe(container)).toHaveNoViolations();
  });
});
