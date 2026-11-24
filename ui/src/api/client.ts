// Typed client for the TenderPy API. Components call these functions and
// never fetch directly, so response shapes are checked in one place.

const API_BASE = "/api";

// Mirrors MAX_LIST_LIMIT in api/app.py.
export const MAX_LIST_LIMIT = 200;

export interface TenderSummary {
  id: number;
  reference_number: string | null;
  tender_object: string | null;
  public_buyer: string | null;
  // ISO 8601 with Morocco's offset, e.g. "2026-11-04T10:00:00+01:00".
  deadline: string | null;
  has_dce_archive: boolean;
}

export interface TenderDetail {
  id: number;
  tender_id: string | null;
  organization_acronym: string | null;
  reference_number: string | null;
  tender_object: string | null;
  public_buyer: string | null;
  location: string | null;
  category: string | null;
  procurement_type: string | null;
  // ISO date, e.g. "2026-10-03".
  publication_date: string | null;
  // ISO 8601 with Morocco's offset, e.g. "2026-11-04T10:00:00+01:00".
  deadline: string | null;
  has_dce_archive: boolean;
}

// An open tender closing within 14 days, as listed on the Insights page.
export interface ClosingSoonTender {
  id: number;
  reference_number: string | null;
  tender_object: string | null;
  public_buyer: string | null;
  // ISO 8601 with Morocco's offset, e.g. "2026-11-04T10:00:00+01:00".
  deadline: string;
}

// Open tenders by time left, each bucket nearest deadline first: less than
// 3 days, 3 to 7 days, and 7 to 14 days.
export interface ClosingSoon {
  lt3: ClosingSoonTender[];
  "3to7": ClosingSoonTender[];
  "7to14": ClosingSoonTender[];
}

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { signal });
  if (!response.ok) {
    throw new ApiError(response.status, `GET ${path} failed with ${response.status}`);
  }
  return (await response.json()) as T;
}

// With closingSoon, only open tenders closing within 14 days, nearest
// deadline first; otherwise every tender, newest publication first.
export function listTenders(
  { limit, offset, closingSoon }: { limit?: number; offset?: number; closingSoon?: boolean } = {},
  signal?: AbortSignal,
): Promise<TenderSummary[]> {
  const params = new URLSearchParams();
  if (limit !== undefined) params.set("limit", String(limit));
  if (offset !== undefined) params.set("offset", String(offset));
  if (closingSoon) params.set("closing_soon", "true");
  const query = params.size > 0 ? `?${params}` : "";
  return getJson<TenderSummary[]>(`/tenders${query}`, signal);
}

export function getClosingSoon(signal?: AbortSignal): Promise<ClosingSoon> {
  return getJson<ClosingSoon>("/insights/closing-soon", signal);
}

// Rejects with an ApiError of status 404 when the tender does not exist.
export function getTender(id: string, signal?: AbortSignal): Promise<TenderDetail> {
  return getJson<TenderDetail>(`/tenders/${encodeURIComponent(id)}`, signal);
}

// URL of a tender's DCE archive; only link to it when has_dce_archive is
// true. Used as a plain link so the browser handles the download itself; the
// API streams the zip from document storage.
export function dceArchiveUrl(id: number): string {
  return `${API_BASE}/tenders/${id}/dce-archive`;
}
