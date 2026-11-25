import { splitDeadline } from "../dates";

// A deadline's date with its time (HH:mm, Moroccan local time) on the line
// below. A muted dash stands in for a missing deadline.
export function Deadline({ value }: { value: string | null }) {
  if (!value) return <span className="empty-value">—</span>;
  const { date, time } = splitDeadline(value);
  return (
    <time className="deadline" dateTime={value}>
      <span>{date}</span>
      {time && <span className="deadline__time">{time}</span>}
    </time>
  );
}
