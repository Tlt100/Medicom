import { vi } from 'vitest';
import type { Registry } from '../lib/api';

export const registryFixture: Registry = {
  registry_version: 1,
  last_reviewed: '2026-10-17',
  coverage: { total: 12, verified: 11, needs_review: 1, binding: 5, federal: 9, nj: 3 },
  sources: [
    {
      id: 'nj-dobi-ihcap',
      title: 'Independent Health Care Appeals Program (IHCAP)',
      citation: null,
      authority: 'New Jersey Department of Banking and Insurance',
      url: 'https://www.nj.gov/dobi/division_insurance/managedcare/ihcap.htm',
      jurisdiction: 'NJ',
      source_type: 'official-resource',
      topics: ['external-review'],
      date: null,
      date_label: null,
      last_checked: '2026-10-16',
      excerpts: [{ locator: 'Contact', text: '1-888-393-1062 or 609-777-9470' }],
      verification: 'verified',
      review_note: null,
      version: 1,
    },
  ],
};

export const jsonResponse = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });

export function mockFetchJson(body: unknown, status = 200) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async () => jsonResponse(body, status));
}
