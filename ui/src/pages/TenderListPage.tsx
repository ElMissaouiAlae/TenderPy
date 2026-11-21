import { useEffect, useState } from "react";
import { Link } from "react-router";

import { listTenders, MAX_LIST_LIMIT, type TenderSummary } from "../api/client";

const MAX_OBJECT_LENGTH = 120;

type State =
  | { kind: "loading" }
  | { kind: "error" }
  | { kind: "loaded"; tenders: TenderSummary[] };

function shorten(text: string | null): string {
  if (!text) return "";
  return text.length > MAX_OBJECT_LENGTH ? `${text.slice(0, MAX_OBJECT_LENGTH).trimEnd()}…` : text;
}

// "public buyer · reference number", skipping whichever is missing.
function buyerAndReference(tender: TenderSummary): string {
  return [tender.public_buyer, tender.reference_number].filter(Boolean).join(" · ");
}

export function TenderListPage() {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    const controller = new AbortController();
    // No pagination controls yet, so ask for as many as the API allows.
    listTenders({ limit: MAX_LIST_LIMIT }, controller.signal)
      .then((tenders) => setState({ kind: "loaded", tenders }))
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          console.error(error);
          setState({ kind: "error" });
        }
      });
    return () => controller.abort();
  }, []);

  return (
    <section className="page">
      {/* The page title is the top bar's heading. */}
      <p className="page__description">Every tender whose DCE archive is available.</p>
      <div className="card card--table">
        {state.kind === "loading" && <p className="card__message message">Loading tenders…</p>}
        {state.kind === "error" && (
          <p className="card__message message message--error">
            Could not load tenders. Check that the API is running and try again.
          </p>
        )}
        {state.kind === "loaded" && state.tenders.length === 0 && (
          <p className="card__message message">No tender has a DCE archive yet.</p>
        )}
        {state.kind === "loaded" && state.tenders.length > 0 && (
          <div className="table-scroll">
            <table className="tender-table">
              <thead>
                <tr>
                  <th scope="col">Tender</th>
                  <th scope="col">Deadline</th>
                </tr>
              </thead>
              <tbody>
                {state.tenders.map((tender) => {
                  const meta = buyerAndReference(tender);
                  return (
                    <tr key={tender.id} className="tender-table__row">
                      <td>
                        {/* Stretched over the whole row, so the row is one link. */}
                        <Link
                          to={`/tenders/${tender.id}`}
                          className="tender-table__link"
                          // The link covers the row, so it carries the full object's tooltip.
                          title={tender.tender_object ?? undefined}
                        >
                          {shorten(tender.tender_object) || "Untitled tender"}
                        </Link>
                        {meta && <span className="tender-table__meta">{meta}</span>}
                      </td>
                      <td className="tender-table__deadline">{tender.tender_end_date}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}
