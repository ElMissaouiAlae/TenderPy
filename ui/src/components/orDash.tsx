import type { ReactNode } from "react";

// A muted dash stands in for a missing value.
export function orDash(value: string | null): ReactNode {
  return value || <span className="empty-value">—</span>;
}
