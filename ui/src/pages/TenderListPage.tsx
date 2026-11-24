import { useEffect, useState, type ReactNode } from "react";
import { Link, useSearchParams } from "react-router";

import { dceArchiveUrl, listTenders, type TenderSummary } from "../api/client";
import { Deadline } from "../components/Deadline";

const PAGE_SIZE = 20;
const MAX_OBJECT_LENGTH = 120;

type State =
  | { kind: "loading" }
  | { kind: "error" }
  | { kind: "loaded"; tenders: TenderSummary[] };

// `?page=N` is 1-based. Anything missing, non-numeric or below 1 is page 1.
function parsePage(raw: string | null): number {
  const page = Number(raw);
  return Number.isSafeInteger(page) && page >= 1 ? page : 1;
}

// The object, shortened when long, as the row's visible name.
function tenderTitle(tender: TenderSummary): string {
  const text = tender.tender_object;
  if (!text) return "Untitled tender";
  return text.length > MAX_OBJECT_LENGTH ? `${text.slice(0, MAX_OBJECT_LENGTH).trimEnd()}…` : text;
}

// A muted dash stands in for a missing value.
function orDash(value: string | null): ReactNode {
  return value || <span className="empty-value">—</span>;
}

export function TenderListPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const page = parsePage(searchParams.get("page"));
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    const controller = new AbortController();
    setState({ kind: "loading" });
    listTenders({ limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE }, controller.signal)
      .then((tenders) => setState({ kind: "loaded", tenders }))
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          console.error(error);
          setState({ kind: "error" });
        }
      });
    return () => controller.abort();
  }, [page]);

  function goToPage(target: number) {
    setSearchParams(target === 1 ? {} : { page: String(target) });
    // The pager sits below the table, so start the new page from its top.
    window.scrollTo(0, 0);
  }

  // The API returns no total, so a short page is the only sign of the last one.
  const hasNext = state.kind === "loaded" && state.tenders.length === PAGE_SIZE;

  return (
    <section className="page">
      {/* The page title is the top bar's heading. */}
      <p className="page__description">Every discovered tender.</p>
      <div className="card card--table">
        {state.kind === "loading" && <p className="card__message message">Loading tenders…</p>}
        {state.kind === "error" && (
          <p className="card__message message message--error">
            Could not load tenders. Check that the API is running and try again.
          </p>
        )}
        {state.kind === "loaded" && state.tenders.length === 0 && (
          <p className="card__message message">
            {page === 1 ? "No tender has been discovered yet." : "No more tenders."}
          </p>
        )}
        {state.kind === "loaded" && state.tenders.length > 0 && (
          <div className="table-scroll">
            <table className="tender-table">
              <thead>
                <tr>
                  <th scope="col">Object</th>
                  <th scope="col">Reference</th>
                  <th scope="col">Public buyer</th>
                  <th scope="col">Deadline</th>
                  <th scope="col">
                    <span className="visually-hidden">DCE archive</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {state.tenders.map((tender) => {
                  const title = tenderTitle(tender);
                  return (
                    <tr key={tender.id} className="tender-table__row">
                      <td className="tender-table__object">
                        {/* Stretched over the whole row, so the row is one link. */}
                        <Link
                          to={`/tenders/${tender.id}`}
                          className="tender-table__link"
                          title={tender.tender_object ?? undefined}
                        >
                          {title}
                        </Link>
                      </td>
                      <td className="tender-table__reference">{orDash(tender.reference_number)}</td>
                      <td className="tender-table__buyer">{orDash(tender.public_buyer)}</td>
                      <td className="tender-table__deadline">
                        <Deadline value={tender.deadline} />
                      </td>
                      <td className="tender-table__download">
                        {/* Sits above the row link, so it downloads without opening the tender. */}
                        {tender.has_dce_archive && (
                          <a
                            href={dceArchiveUrl(tender.id)}
                            className="button button--outline"
                            // Every row's button reads "Download", so name the tender too.
                            aria-label={`Download DCE archive: ${title}`}
                            download
                          >
                            Download
                          </a>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
      <nav className="pager" aria-label="Pagination">
        <button
          type="button"
          className="pager__button"
          disabled={page === 1}
          onClick={() => goToPage(page - 1)}
        >
          <ChevronIcon direction="left" />
          Previous
        </button>
        <button
          type="button"
          className="pager__button"
          disabled={!hasNext}
          onClick={() => goToPage(page + 1)}
        >
          Next
          <ChevronIcon direction="right" />
        </button>
      </nav>
    </section>
  );
}

function ChevronIcon({ direction }: { direction: "left" | "right" }) {
  return (
    <svg width="7" height="12" viewBox="0 0 7 12" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={direction === "left" ? "M6 1 1 6l5 5" : "m1 1 5 5-5 5"} />
    </svg>
  );
}
