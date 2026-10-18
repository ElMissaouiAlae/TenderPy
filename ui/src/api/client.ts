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
  tender_end_date: string | null;
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

export function listTenders(
  { limit, offset }: { limit?: number; offset?: number } = {},
  signal?: AbortSignal,
): Promise<TenderSummary[]> {
  const params = new URLSearchParams();
  if (limit !== undefined) params.set("limit", String(limit));
  if (offset !== undefined) params.set("offset", String(offset));
  const query = params.size > 0 ? `?${params}` : "";
  return getJson<TenderSummary[]>(`/tenders${query}`, signal);
}
