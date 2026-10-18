import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, useLocation } from 'react-router-dom';
import { axe } from 'vitest-axe';
import { App } from '../App';
import { RegistrySchema, type ClaimSummary } from '../lib/api';
import { claimsBySource, daysSinceChecked, EMPTY_FILTERS, filterSources, isDueForRecheck } from '../lib/library';
import { jsonResponse } from './fixtures';
import claimsJson from './fixtures/claims.json';
import registryJson from './fixtures/registry.json';

const registry = RegistrySchema.parse(registryJson);
const claims = claimsJson as ClaimSummary[];
const byId = claimsBySource(claims);
const ids = (filters: Partial<typeof EMPTY_FILTERS>) => filterSources(registry.sources, { ...EMPTY_FILTERS, ...filters }, byId).map((s) => s.id);

// ---------------------------------------------------------------- filter logic

describe('filterSources', () => {
  it('returns everything with no filters', () => {
    expect(ids({})).toHaveLength(registry.sources.length);
  });

  it('filters by jurisdiction, legal weight, topic and status', () => {
    expect(ids({ jurisdiction: 'NJ' }).every((id) => id.startsWith('nj-'))).toBe(true);
    expect(ids({ weight: 'binding' }).every((id) => id.startsWith('cfr-'))).toBe(true);
    expect(ids({ topic: 'medicaid' })).toContain('cfr-42-438-subpart-f');
    expect(ids({ status: 'needs-review' })).toEqual(['nj-dmahs-mc-26-06']);
  });

  it('searches titles, verbatim excerpts and the statements that cite a source, all words required', () => {
    expect(ids({ q: 'IHCAP' })).toContain('nj-dobi-ihcap');
    expect(ids({ q: '72 hours' })).toContain('cfr-29-2560-503-1');
    expect(ids({ q: 'grandfathered March' })).toEqual(['dol-filing-a-claim']);
    expect(ids({ q: 'zzzz-not-there' })).toEqual([]);
  });
});

describe('re-check dates', () => {
  it('counts calendar days and flags sources older than 180 days', () => {
    expect(daysSinceChecked('2026-10-16', new Date(2026, 9, 17))).toBe(1);
    expect(isDueForRecheck('2026-04-19', new Date(2026, 9, 17))).toBe(true); // 181 days
    expect(isDueForRecheck('2026-04-20', new Date(2026, 9, 17))).toBe(false); // 180 days
  });
});

// ---------------------------------------------------------------- the page

function mockApi(fail = false) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
    const url = typeof input === 'string' ? input : input instanceof URL ? input.pathname : input.url;
    if (fail) throw new TypeError('offline');
    if (url === '/api/sources') return jsonResponse(registryJson);
    if (url === '/api/claims') return jsonResponse(claimsJson);
    return jsonResponse({ error: 'not_found', message: 'Not found.' }, 404);
  });
}

function LocationProbe() {
  const { search } = useLocation();
  return <output data-testid="search">{search}</output>;
}

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
      <LocationProbe />
    </MemoryRouter>,
  );
}

const cards = () => document.querySelectorAll('article.source-card');

describe('Source library page', () => {
  it('lists every source with coverage numbers', async () => {
    mockApi();
    renderAt('/sources');
    await screen.findByText(`Showing ${registry.sources.length} of ${registry.sources.length} sources`);
    expect(cards()).toHaveLength(registry.sources.length);
    expect(screen.getByText('Statements citing them').nextElementSibling).toHaveTextContent(String(claims.length));
  });

  it('shows the full record for a source: weight, dates, excerpts, citing statements and official link', async () => {
    mockApi();
    renderAt('/sources');
    const card = (await screen.findByRole('heading', { name: 'Claims procedure for employee benefit plans (ERISA)' })).closest('article')!;
    expect(within(card).getByText('Regulation')).toBeInTheDocument();
    expect(within(card).getByText('Verified')).toBeInTheDocument();
    expect(within(card).getByText('eCFR text current as of')).toBeInTheDocument();
    expect(within(card).getByText(/Provide claimants at least 180 days/)).toBeInTheDocument();
    expect(within(card).getByText('§ 2560.503-1(h)(3)(i)')).toBeInTheDocument();
    expect(within(card).getByText(/you get at least 180 days after receiving a denial/i)).toBeInTheDocument();
    const link = within(card).getByRole('link', { name: /open the official source/i });
    expect(link.getAttribute('href')).toMatch(/^https:\/\/www\.ecfr\.gov\//);
    expect(link).toHaveAttribute('rel', 'noopener noreferrer');
  });

  it('explains why a flagged source is flagged', async () => {
    mockApi();
    renderAt('/sources?status=needs-review');
    await screen.findByText(`Showing 1 of ${registry.sources.length} sources`);
    const card = cards()[0] as HTMLElement;
    expect(within(card).getByText('Flagged for review')).toBeInTheDocument();
    expect(within(card).getByText('Why this is flagged')).toBeInTheDocument();
    expect(card).toHaveTextContent(/needs human review/);
  });

  it('filters from the controls and keeps filters in the URL', async () => {
    mockApi();
    renderAt('/sources');
    await screen.findByText(/^Showing/);
    await userEvent.selectOptions(screen.getByLabelText('Jurisdiction'), 'NJ');
    const nj = registry.sources.filter((s) => s.jurisdiction === 'NJ').length;
    expect(screen.getByText(`Showing ${nj} of ${registry.sources.length} sources`)).toBeInTheDocument();
    expect(screen.getByTestId('search')).toHaveTextContent('?jurisdiction=NJ');
    await userEvent.click(screen.getByRole('button', { name: /clear filters/i }));
    expect(cards()).toHaveLength(registry.sources.length);
  });

  it('search with no matches shows a helpful empty state', async () => {
    mockApi();
    renderAt('/sources');
    await screen.findByText(/^Showing/);
    await userEvent.type(screen.getByRole('searchbox', { name: 'Search' }), 'zzzz');
    expect(screen.getByRole('heading', { name: /no sources match/i })).toBeInTheDocument();
    await userEvent.click(screen.getAllByRole('button', { name: /clear filters/i })[0]!);
    expect(cards()).toHaveLength(registry.sources.length);
  });

  it('ignores invalid filter values in the URL', async () => {
    mockApi();
    renderAt('/sources?jurisdiction=<script>&status=bogus');
    expect(await screen.findByText(`Showing ${registry.sources.length} of ${registry.sources.length} sources`)).toBeInTheDocument();
  });

  it('a deep link highlights the source and opens its excerpts', async () => {
    mockApi();
    renderAt('/sources#source-nj-dobi-ihcap');
    await screen.findByText(/^Showing/);
    const card = document.getElementById('source-nj-dobi-ihcap')!;
    expect(card).toHaveClass('source-highlight');
    expect(card.querySelector('details.excerpts')).toHaveAttribute('open');
    expect(document.activeElement).toBe(card);
  });

  it('shows an error with a retry', async () => {
    const spy = mockApi(true);
    renderAt('/sources');
    expect(await screen.findByRole('alert')).toHaveTextContent(/couldn’t load/i);
    spy.mockRestore();
    mockApi();
    await userEvent.click(screen.getByRole('button', { name: /try again/i }));
    expect(await screen.findByText(/^Showing/)).toBeInTheDocument();
  });

  it('has no detectable accessibility violations', async () => {
    mockApi();
    const { container } = renderAt('/sources');
    await screen.findByText(/^Showing/);
    expect(await axe(container)).toHaveNoViolations();
  });
});
