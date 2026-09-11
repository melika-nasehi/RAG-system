import { parseSource, timeAgo, toPersianDigits } from './persian';

describe('toPersianDigits', () => {
  it('converts ASCII digits', () => {
    expect(toPersianDigits('صفحه 12')).toBe('صفحه ۱۲');
    expect(toPersianDigits(2024)).toBe('۲۰۲۴');
  });
});

describe('parseSource', () => {
  it('splits a document label and its page', () => {
    expect(parseSource('آیین‌نامه آموزشی.pdf، صفحه 7')).toEqual({
      document: 'آیین‌نامه آموزشی',
      page: '۷',
    });
  });

  it('handles a label with no page', () => {
    expect(parseSource('سند بدون صفحه.pdf')).toEqual({
      document: 'سند بدون صفحه',
      page: null,
    });
  });
});

describe('timeAgo', () => {
  it('reports very recent times as "همین حالا"', () => {
    expect(timeAgo(new Date().toISOString())).toBe('همین حالا');
  });

  it('reports minutes with Persian digits', () => {
    const tenMinAgo = new Date(Date.now() - 10 * 60 * 1000).toISOString();
    expect(timeAgo(tenMinAgo)).toBe('۱۰ دقیقه پیش');
  });

  it('returns an empty string for an invalid date', () => {
    expect(timeAgo('not-a-date')).toBe('');
  });
});
