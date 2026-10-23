import { useEffect, useState } from "react";
import { Link, useParams } from "react-router";

import { ApiError, getTender, type TenderDetail } from "../api/client";

type State =
  | { kind: "loading" }
  | { kind: "not-found" }
  | { kind: "error" }
  | { kind: "loaded"; tender: TenderDetail };

// Shows a missing field explicitly, so it isn't mistaken for broken layout.
function Value({ value }: { value: string | null }) {
  return value ? <>{value}</> : <span className="placeholder">Not recorded</span>;
}

export function TenderDetailPage() {
  const { id = "" } = useParams();
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    // Ids are database keys; anything else can't be a tender, and the API
    // would reject it as invalid rather than not found.
    if (!/^\d+$/.test(id)) {
      setState({ kind: "not-found" });
      return;
    }
    const controller = new AbortController();
    setState({ kind: "loading" });
    getTender(id, controller.signal)
      .then((tender) => setState({ kind: "loaded", tender }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        if (error instanceof ApiError && error.status === 404) {
          setState({ kind: "not-found" });
        } else {
          console.error(error);
          setState({ kind: "error" });
        }
      });
    return () => controller.abort();
  }, [id]);

  return (
    <section className="tender-detail">
      <Link to="/tenders" className="back-link">
        ← Back to tenders
      </Link>
      {state.kind === "loading" && <p className="message">Loading tender…</p>}
      {state.kind === "not-found" && (
        <p className="message">
          This tender was not found. It may not exist, or its DCE archive is not available.
        </p>
      )}
      {state.kind === "error" && (
        <p className="message message--error">
          Could not load this tender. Check that the API is running and try again.
        </p>
      )}
      {state.kind === "loaded" && <TenderDetailView tender={state.tender} />}
    </section>
  );
}

function TenderDetailView({ tender }: { tender: TenderDetail }) {
  return (
    <>
      <header className="tender-detail__header">
        {(tender.category || tender.procurement_type) && (
          <div className="pills">
            {tender.category && <span className="pill pill--accent">{tender.category}</span>}
            {tender.procurement_type && <span className="pill">{tender.procurement_type}</span>}
          </div>
        )}
        <h1 className="tender-detail__title">
          <Value value={tender.tender_object} />
        </h1>
        <p className="tender-detail__meta">
          <Value value={tender.public_buyer} /> · Ref. <Value value={tender.reference_number} /> ·
          Published <Value value={tender.publication_date} />
        </p>
      </header>
      <section className="card" aria-labelledby="key-facts-title">
        <h2 id="key-facts-title" className="card__title">
          Key facts
        </h2>
        <dl className="facts">
          <div className="fact">
            <dt>Tender ID</dt>
            <dd>
              <Value value={tender.tender_id} />
            </dd>
          </div>
          <div className="fact">
            <dt>Organization acronym</dt>
            <dd>
              <Value value={tender.organization_acronym} />
            </dd>
          </div>
          <div className="fact">
            <dt>Location</dt>
            <dd>
              <Value value={tender.location} />
            </dd>
          </div>
          <div className="fact">
            <dt>End date</dt>
            <dd>
              <Value value={tender.tender_end_date} />
            </dd>
          </div>
        </dl>
      </section>
    </>
  );
}
