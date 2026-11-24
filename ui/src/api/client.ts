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

// How far back, by publication date, the period-aware insights look.
// Mirrors Period in persistence/insights.py.
export type Period = "7d" | "30d" | "90d" | "all";

export const DEFAULT_PERIOD: Period = "30d";

// The filter shared by the period-aware Insights sections.
export interface InsightsFilter {
  period: Period;
  // Only open tenders (deadline still in the future).
  openOnly: boolean;
}

// What the period-aware insights are based on.
export interface Coverage {
  tender_count: number;
  // ISO dates, e.g. "2026-10-03"; null when no tender is counted.
  earliest_publication_date: string | null;
  latest_publication_date: string | null;
  without_deadline_count: number;
}

// A tender published in the last 7 days, as listed on the Insights page.
export interface NewTender {
  id: number;
  reference_number: string | null;
  tender_object: string | null;
  public_buyer: string | null;
  // ISO date, e.g. "2026-10-03".
  publication_date: string;
  // ISO 8601 with Morocco's offset, e.g. "2026-11-04T10:00:00+01:00".
  deadline: string | null;
}

// What the top counts can be by. Mirrors TopDimension in persistence/insights.py.
export type TopDimension = "public_buyer" | "category" | "location";

// One value of a dimension and how many tenders have it. Names that differ
// only in case or spacing are counted together, under their most frequent
// spelling.
export interface TopValue {
  label: string;
  tender_count: number;
}

// What median response windows can be grouped by. Mirrors
// ResponseWindowDimension in persistence/insights.py.
export type ResponseWindowDimension = "category" | "public_buyer";

// The median response window of one category or public buyer.
export interface ResponseWindowGroup {
  label: string;
  // Days; may end in .5 for an even-sized group.
  median_days: number;
  tender_count: number;
}

// A tender whose response window is under half its category's median.
export interface ShortResponseWindow {
  id: number;
  reference_number: string | null;
  tender_object: string | null;
  public_buyer: string | null;
  category: string;
  response_window_days: number;
  category_median_days: number;
}

// Groups most tenders first; short response windows shortest first.
export interface ResponseWindows {
  groups: ResponseWindowGroup[];
  short_response_windows: ShortResponseWindow[];
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

function filterParams({ period, openOnly }: InsightsFilter): URLSearchParams {
  const params = new URLSearchParams({ period });
  if (openOnly) params.set("open_only", "true");
  return params;
}

export function getCoverage(filter: InsightsFilter, signal?: AbortSignal): Promise<Coverage> {
  return getJson<Coverage>(`/insights/coverage?${filterParams(filter)}`, signal);
}

// The values of a dimension with the most tenders in the period, most first.
export function getTop(
  filter: InsightsFilter,
  { dimension, limit }: { dimension: TopDimension; limit?: number },
  signal?: AbortSignal,
): Promise<TopValue[]> {
  const params = filterParams(filter);
  params.set("dimension", dimension);
  if (limit !== undefined) params.set("limit", String(limit));
  return getJson<TopValue[]>(`/insights/top?${params}`, signal);
}

// Median response window per group in the period, and the short ones.
export function getResponseWindows(
  filter: InsightsFilter,
  dimension: ResponseWindowDimension,
  signal?: AbortSignal,
): Promise<ResponseWindows> {
  const params = filterParams(filter);
  params.set("dimension", dimension);
  return getJson<ResponseWindows>(`/insights/response-window?${params}`, signal);
}

// Tenders published in the last 7 days, newest first, whatever the period.
export function getNewThisWeek(
  { openOnly }: { openOnly: boolean },
  signal?: AbortSignal,
): Promise<NewTender[]> {
  const query = openOnly ? "?open_only=true" : "";
  return getJson<NewTender[]>(`/insights/new-this-week${query}`, signal);
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
