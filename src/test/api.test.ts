import { fetchRegistry } from '../core/api/sources';
import { formatDate } from '../core/api/http';
import { mockFetchJson, registryFixture } from './fixtures';

describe('fetchRegistry', () => {
  it('returns validated registry data', async () => {
    mockFetchJson(registryFixture);
    const data = await fetchRegistry();
    expect(data.coverage.total).toBe(12);
    expect(data.sources[0]?.id).toBe('nj-dobi-ihcap');
  });

  it('rejects a response with the wrong shape instead of rendering it', async () => {
    mockFetchJson({ sources: 'not-a-list' });
    await expect(fetchRegistry()).rejects.toThrow('unexpected format');
  });

  it.each(['javascript:alert(1)', 'http://www.nj.gov/dobi/', 'data:text/html,hi'])('rejects a non-https source link: %s', async (url) => {
    const bad = structuredClone(registryFixture);
    bad.sources[0]!.url = url;
    mockFetchJson(bad);
    await expect(fetchRegistry()).rejects.toThrow('unexpected format');
  });

  it('turns HTTP errors into a readable message', async () => {
    mockFetchJson({ error: 'server_error' }, 500);
    await expect(fetchRegistry()).rejects.toThrow('(500)');
  });

  it('explains a platform-level 413 that has no JSON body', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('Request Entity Too Large', { status: 413 }));
    await expect(fetchRegistry()).rejects.toThrow('too large. The limit is 4 MB');
  });

  it('turns network failures into a readable message', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('Failed to fetch'));
    await expect(fetchRegistry()).rejects.toThrow('couldn’t reach');
  });
});

describe('formatDate', () => {
  it('formats ISO dates without time-zone drift', () => {
    expect(formatDate('2026-10-17')).toBe('October 17, 2026');
  });
});
