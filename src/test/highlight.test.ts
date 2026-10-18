import { segmentText } from '../core/lib/highlight';

describe('segmentText', () => {
  const text = 'You must appeal within 180 days. Call us.';

  it('returns plain text when there are no citations', () => {
    expect(segmentText(text, [])).toEqual([{ text, ids: [] }]);
  });

  it('marks a cited span and keeps the rest plain', () => {
    const segs = segmentText(text, [{ id: 'a', start: 0, end: 32 }]);
    expect(segs).toEqual([
      { text: 'You must appeal within 180 days.', ids: ['a'] },
      { text: ' Call us.', ids: [] },
    ]);
  });

  it('splits overlapping citations into non-overlapping pieces covering both ids', () => {
    const segs = segmentText(text, [
      { id: 'sentence', start: 0, end: 32 },
      { id: 'deadline', start: 16, end: 31 },
    ]);
    expect(segs.map((s) => s.text).join('')).toBe(text);
    expect(segs.find((s) => s.text === 'within 180 days')?.ids).toEqual(['sentence', 'deadline']);
  });

  it('ignores out-of-range spans instead of corrupting the text', () => {
    const segs = segmentText(text, [{ id: 'bad', start: 10, end: 999 }]);
    expect(segs).toEqual([{ text, ids: [] }]);
  });
});
