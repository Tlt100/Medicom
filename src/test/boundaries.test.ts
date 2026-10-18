// Shared core code must never depend on a feature module, and features must not depend on each other.
const sources = import.meta.glob<string>(['../core/**/*.{ts,tsx}', '../features/**/*.{ts,tsx}'], {
  query: '?raw',
  import: 'default',
  eager: true,
});

const importsOf = (code: string) => [...code.matchAll(/from\s+'([^']+)'/g)].map((m) => m[1]!);

describe('module boundaries', () => {
  it('finds the files it checks', () => {
    expect(Object.keys(sources).some((p) => p.includes('/core/'))).toBe(true);
    expect(Object.keys(sources).some((p) => p.includes('/features/denials/'))).toBe(true);
  });

  it('core never imports from features', () => {
    const offenders = Object.entries(sources)
      .filter(([path]) => path.includes('/core/'))
      .filter(([, code]) => importsOf(code).some((spec) => spec.includes('features/')));
    expect(offenders.map(([path]) => path)).toEqual([]);
  });

  it('features do not import each other', () => {
    const offenders = Object.entries(sources)
      .filter(([path]) => path.includes('/features/'))
      .filter(([path, code]) => {
        const own = path.split('/features/')[1]!.split('/')[0];
        return importsOf(code).some((spec) => /features\/([^/]+)/.exec(spec)?.[1] !== undefined && /features\/([^/]+)/.exec(spec)![1] !== own);
      });
    expect(offenders.map(([path]) => path)).toEqual([]);
  });
});
