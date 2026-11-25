// Formats the API's dates for display. The API sends a deadline as ISO 8601
// already in Moroccan local time (e.g. "2026-11-04T10:00:00+01:00") and a
// publication date as an ISO date ("2026-10-03"). Both are read straight from
// the string, never through Date, so the browser's timezone can't shift them.

const ISO_DATE = /^(\d{4})-(\d{2})-(\d{2})/;
const ISO_TIME = /T(\d{2}):(\d{2})/;

// "2026-10-03" (or the date part of a datetime) as "03/10/2026", the
// platform's own format.
export function formatDate(iso: string): string {
  const match = ISO_DATE.exec(iso);
  if (!match) return iso;
  const [, year, month, day] = match;
  return `${day}/${month}/${year}`;
}

// The deadline's date and its time of day (HH:mm), as Morocco shows them.
export function splitDeadline(iso: string): { date: string; time: string | null } {
  const time = ISO_TIME.exec(iso);
  return { date: formatDate(iso), time: time ? `${time[1]}:${time[2]}` : null };
}
