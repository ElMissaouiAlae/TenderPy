const DAY_MS = 24 * 60 * 60 * 1000;

// Whole days until a deadline, or null once it has passed. Compares
// instants, so the browser's timezone doesn't matter.
function daysLeft(deadline: string, now: number = Date.now()): number | null {
  const remaining = Date.parse(deadline) - now;
  if (Number.isNaN(remaining) || remaining <= 0) return null;
  return Math.floor(remaining / DAY_MS);
}

// The days-left badge of an open tender. Closed tenders and tenders without
// a deadline get none. Its urgency follows the closing-soon buckets: under
// 3 days, under 7 days, then the rest.
export function DaysLeft({ deadline }: { deadline: string | null }) {
  if (!deadline) return null;
  const days = daysLeft(deadline);
  if (days === null) return null;
  const urgency = days < 3 ? "urgent" : days < 7 ? "soon" : "later";
  const label = days === 0 ? "Under 1 day left" : days === 1 ? "1 day left" : `${days} days left`;
  return <span className={`days-left days-left--${urgency}`}>{label}</span>;
}
