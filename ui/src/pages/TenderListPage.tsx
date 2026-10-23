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
    <section>
      <h1>Tenders</h1>
      {state.kind === "loading" && <p className="message">Loading tenders…</p>}
      {state.kind === "error" && (
        <p className="message message--error">
          Could not load tenders. Check that the API is running and try again.
        </p>
      )}
      {state.kind === "loaded" && state.tenders.length === 0 && (
        <p className="message">No tender has a DCE archive yet.</p>
      )}
      {state.kind === "loaded" && state.tenders.length > 0 && (
        <table className="tender-table">
          <thead>
            <tr>
              <th>Reference</th>
              <th>Object</th>
              <th>Public buyer</th>
              <th>End date</th>
            </tr>
          </thead>
          <tbody>
            {state.tenders.map((tender) => (
              <tr key={tender.id} className="tender-table__row">
                <td>
                  {/* Stretched over the whole row, so the row is one link. */}
                  <Link
                    to={`/tenders/${tender.id}`}
                    className="tender-table__link"
                    // The link covers the row, so it carries the full object's tooltip.
                    title={tender.tender_object ?? undefined}
                  >
                    {tender.reference_number || "View tender"}
                  </Link>
                </td>
                <td>{shorten(tender.tender_object)}</td>
                <td>{tender.public_buyer}</td>
                <td className="nowrap">{tender.tender_end_date}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
