import { useEffect, useState, type ReactNode } from "react";
import { Link, useParams } from "react-router";

import { ApiError, dceArchiveUrl, getTender, type TenderDetail } from "../api/client";
import { Deadline } from "../components/Deadline";
import { formatDate } from "../dates";

type State =
  | { kind: "loading" }
  | { kind: "not-found" }
  | { kind: "error" }
  | { kind: "loaded"; tender: TenderDetail };

// A muted dash stands in for a missing value, as in the tender list.
function Value({ value }: { value: string | null }) {
  return value ? <>{value}</> : <span className="empty-value">—</span>;
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
        <span aria-hidden="true">←</span> Back to tenders
      </Link>
      {state.kind === "loading" && (
        <div className="card">
          <p className="message">Loading tender…</p>
        </div>
      )}
      {state.kind === "not-found" && (
        <div className="card">
          <p className="message">
            This tender was not found.
          </p>
        </div>
      )}
      {state.kind === "error" && (
        <div className="card">
          <p className="message message--error">
            Could not load this tender. Check that the API is running and try again.
          </p>
        </div>
      )}
      {state.kind === "loaded" && <TenderDetailView tender={state.tender} />}
    </section>
  );
}

// One entry of the "Key facts" card: a muted label over its value.
function Fact({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="fact">
      <dt>{label}</dt>
      <dd>{children}</dd>
    </div>
  );
}

function TenderDetailView({ tender }: { tender: TenderDetail }) {
  return (
    <>
      <header className="tender-detail__header">
        {(tender.category || tender.procurement_type) && (
          <div className="tags">
            {tender.category && <span className="tag tag--accent">{tender.category}</span>}
            {tender.procurement_type && <span className="tag">{tender.procurement_type}</span>}
          </div>
        )}
        {/* h2: the top bar's "Tenders" is the page's h1. */}
        <h2 className="tender-detail__title">
          <Value value={tender.tender_object} />
        </h2>
        <p className="tender-detail__meta">
          <Value value={tender.public_buyer} /> · Ref. <Value value={tender.reference_number} /> ·
          Published <Value value={tender.publication_date && formatDate(tender.publication_date)} />
        </p>
        {tender.has_dce_archive && (
          <div className="tender-detail__actions">
            {/* A plain link, so the browser handles the download itself. */}
            <a className="button button--primary" href={dceArchiveUrl(tender.id)}>
              Download DCE archive
            </a>
          </div>
        )}
      </header>
      {/* The template titles its cards from above, as with "My Cards". */}
      <section className="section" aria-labelledby="key-facts-title">
        <h3 id="key-facts-title" className="section__title">
          Key facts
        </h3>
        <div className="card">
          <dl className="facts">
            <Fact label="Tender ID">
              <Value value={tender.tender_id} />
            </Fact>
            <Fact label="Organization acronym">
              <Value value={tender.organization_acronym} />
            </Fact>
            <Fact label="Location">
              <Value value={tender.location} />
            </Fact>
            <Fact label="Deadline">
              <Deadline value={tender.deadline} />
            </Fact>
          </dl>
        </div>
      </section>
    </>
  );
}
