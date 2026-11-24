import { useEffect, useState } from "react";
import { Link } from "react-router";

import { getClosingSoon, type ClosingSoon, type ClosingSoonTender } from "../api/client";
import { DaysLeft } from "../components/DaysLeft";
import { Deadline } from "../components/Deadline";
import { orDash } from "../components/orDash";

// A market-wide view of discovered tenders. Each section loads on its own,
// with its own loading, empty and error states, so one failing section
// doesn't blank the page.
export function InsightsPage() {
  return (
    <section className="page">
      {/* The page title is the top bar's heading. */}
      <p className="page__description">A market-wide view of discovered tenders.</p>
      <ClosingSoonSection />
    </section>
  );
}

type ClosingSoonState =
  | { kind: "loading" }
  | { kind: "error" }
  | { kind: "loaded"; closingSoon: ClosingSoon };

const BUCKETS: { key: keyof ClosingSoon; label: string }[] = [
  { key: "lt3", label: "Less than 3 days" },
  { key: "3to7", label: "3–7 days" },
  { key: "7to14", label: "7–14 days" },
];

function ClosingSoonSection() {
  const [state, setState] = useState<ClosingSoonState>({ kind: "loading" });

  useEffect(() => {
    const controller = new AbortController();
    getClosingSoon(controller.signal)
      .then((closingSoon) => setState({ kind: "loaded", closingSoon }))
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          console.error(error);
          setState({ kind: "error" });
        }
      });
    return () => controller.abort();
  }, []);

  const isEmpty =
    state.kind === "loaded" && BUCKETS.every(({ key }) => state.closingSoon[key].length === 0);

  return (
    <section className="section" aria-labelledby="closing-soon-title">
      <h2 id="closing-soon-title" className="section__title">
        Closing soon
      </h2>
      <div className="card">
        {state.kind === "loading" && <p className="message">Loading tenders closing soon…</p>}
        {state.kind === "error" && (
          <p className="message message--error">
            Could not load tenders closing soon. Check that the API is running and try again.
          </p>
        )}
        {isEmpty && <p className="message">No open tender closes within the next 14 days.</p>}
        {state.kind === "loaded" && !isEmpty && (
          <div className="closing-soon">
            {BUCKETS.map(({ key, label }) => (
              <ClosingSoonBucket key={key} label={label} tenders={state.closingSoon[key]} />
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

function ClosingSoonBucket({ label, tenders }: { label: string; tenders: ClosingSoonTender[] }) {
  return (
    <section className="closing-soon__bucket">
      <h3 className="closing-soon__title">
        {label} <span className="closing-soon__count">({tenders.length})</span>
      </h3>
      {tenders.length === 0 ? (
        <p className="message">None.</p>
      ) : (
        <ul className="closing-soon__list">
          {tenders.map((tender) => (
            <li key={tender.id}>
              <Link to={`/tenders/${tender.id}`} className="closing-soon__item">
                <span className="closing-soon__main">
                  <span className="closing-soon__object">
                    {tender.tender_object || "Untitled tender"}
                  </span>
                  <span className="closing-soon__meta">
                    Ref. {orDash(tender.reference_number)} · {orDash(tender.public_buyer)}
                  </span>
                </span>
                <span className="closing-soon__deadline">
                  <Deadline value={tender.deadline} />
                  <DaysLeft deadline={tender.deadline} />
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
