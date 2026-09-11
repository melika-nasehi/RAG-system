/** Persian-facing formatting helpers, kept in one place so digits and dates
 *  look consistent wherever they are rendered. */

const FA_DIGITS = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'];

/** Convert every ASCII digit in a string to its Persian equivalent. */
export function toPersianDigits(value: string | number): string {
  return String(value).replace(/[0-9]/g, (d) => FA_DIGITS[Number(d)]);
}

/** A short, human relative time in Persian ("۳ دقیقه پیش", "دیروز"). Falls
 *  back to an absolute Persian date once something is older than a week. */
export function timeAgo(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return '';

  const seconds = Math.round((Date.now() - then) / 1000);
  const minutes = Math.round(seconds / 60);
  const hours = Math.round(minutes / 60);
  const days = Math.round(hours / 24);

  if (seconds < 45) return 'همین حالا';
  if (minutes < 60) return `${toPersianDigits(minutes)} دقیقه پیش`;
  if (hours < 24) return `${toPersianDigits(hours)} ساعت پیش`;
  if (days === 1) return 'دیروز';
  if (days < 7) return `${toPersianDigits(days)} روز پیش`;

  return new Intl.DateTimeFormat('fa-IR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  }).format(then);
}

/** Split a source label of the form "سند.pdf، صفحه 12" into its parts so the
 *  UI can render the page number as a separate pill. */
export function parseSource(raw: string): { document: string; page: string | null } {
  const match = raw.match(/^(.*?)[،,]\s*صفحه\s*([0-9۰-۹]+)\s*$/);
  if (!match) return { document: cleanDocName(raw), page: null };
  return { document: cleanDocName(match[1]), page: toPersianDigits(match[2]) };
}

function cleanDocName(name: string): string {
  return name.trim().replace(/\.pdf$/i, '');
}
