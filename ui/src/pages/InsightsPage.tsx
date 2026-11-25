import { useEffect, useState, type ReactNode } from "react";
import { Link, useSearchParams } from "react-router";

import {
  DEFAULT_PERIOD,
  getClosingSoon,
  getCoverage,
  getNewThisWeek,
  getResponseWindows,
  getTop,
  type ClosingSoon,
  type ClosingSoonTender,
  type InsightsFilter,
  type NewTender,
  type Period,
  type ResponseWindowDimension,
  type TopDimension,
} from "../api/client";
import { DaysLeft } from "../components/DaysLeft";
import { Deadline } from "../components/Deadline";
import { orDash } from "../components/orDash";
import { formatDate } from "../dates";

const PERIODS: { value: Period; label: string }[] = [
  { value: "7d", label: "7 days" },
  { value: "30d", label: "30 days" },
  { value: "90d", label: "90 days" },
  { value: "all", label: "All time" },
];

// `?period=` is one of PERIODS; anything else is the default (30 days).
function parsePeriod(raw: string | null): Period {
  return PERIODS.find(({ value }) => value === raw)?.value ?? DEFAULT_PERIOD;
}

// A market-wide view of discovered tenders. Each section loads on its own,
// with its own loading, empty and error states, so one failing section
// doesn't blank the page. The period and "Open only" live in the URL
// (`?period=7d&open_only=1`) and apply to the sections that accept them.
export function InsightsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const filter: InsightsFilter = {
    period: parsePeriod(searchParams.get("period")),
    openOnly: searchParams.get("open_only") === "1",
  };

  function setFilter({ period, openOnly }: InsightsFilter) {
    const params: Record<string, string> = {};
    if (period !== DEFAULT_PERIOD) params.period = period;
    if (openOnly) params.open_only = "1";
    setSearchParams(params);
  }

  return (
    <section className="page">
      {/* The page title is the top bar's heading. */}
      <div className="page__toolbar">
        <p className="page__description">A market-wide view of discovered tenders.</p>
        <div className="insights-filter">
          <div className="segmented" role="group" aria-label="Period">
            {PERIODS.map(({ value, label }) => (
              <button
                key={value}
                type="button"
                className="filter-toggle"
                aria-pressed={filter.period === value}
                onClick={() => setFilter({ ...filter, period: value })}
              >
                {label}
              </button>
            ))}
          </div>
          <button
            type="button"
            className="filter-toggle"
            aria-pressed={filter.openOnly}
            onClick={() => setFilter({ ...filter, openOnly: !filter.openOnly })}
          >
            Open only
          </button>
        </div>
      </div>
      <CoverageBanner filter={filter} />
      <ClosingSoonSection />
      <NewThisWeekSection openOnly={filter.openOnly} />
      <div className="insights-top">
        <TopSection
          title="Top public buyers"
          dimension="public_buyer"
          filter={filter}
          empty="No public buyer in this period."
        />
        <TopSection
          title="Top categories"
          dimension="category"
          filter={filter}
          empty="No category in this period."
        />
        <TopSection
          title="Top locations"
          dimension="location"
          filter={filter}
          empty="No location in this period."
          note="Only a tender's first location is counted."
        />
      </div>
      <ResponseWindowSection filter={filter} />
    </section>
  );
}

type Load<T> = { kind: "loading" } | { kind: "error" } | { kind: "loaded"; data: T };

// Loads one section's data, again whenever a dependency changes. A newer
// request aborts the older one, so a slow answer never overwrites a newer one.
function useLoad<T>(load: (signal: AbortSignal) => Promise<T>, deps: unknown[]): Load<T> {
  const [state, setState] = useState<Load<T>>({ kind: "loading" });

  useEffect(() => {
    const controller = new AbortController();
    setState({ kind: "loading" });
    load(controller.signal)
      .then((data) => setState({ kind: "loaded", data }))
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          console.error(error);
          setState({ kind: "error" });
        }
      });
    return () => controller.abort();
    // The caller lists what `load` depends on.
  }, deps);

  return state;
}

function CoverageBanner({ filter }: { filter: InsightsFilter }) {
  const { period, openOnly } = filter;
  const state = useLoad((signal) => getCoverage({ period, openOnly }, signal), [period, openOnly]);

  let content: ReactNode;
  if (state.kind === "loading") {
    content = <p className="message">Loading coverage…</p>;
  } else if (state.kind === "error") {
    content = (
      <p className="message message--error">
        Could not load coverage. Check that the API is running and try again.
      </p>
    );
  } else {
    const coverage = state.data;
    content =
      // No tender counted: the API sends no range.
      !coverage.earliest_publication_date || !coverage.latest_publication_date ? (
        <p className="message">
          {openOnly
            ? "No open tender was published in this period."
            : "No tender was published in this period."}
        </p>
      ) : (
        <>
          <p className="coverage__summary">
            Based on {plural(coverage.tender_count, openOnly ? "open tender" : "tender")}{" "}
            published between {formatDate(coverage.earliest_publication_date)} and{" "}
            {formatDate(coverage.latest_publication_date)}.
          </p>
          {coverage.without_deadline_count > 0 && (
            <p className="message">
              {plural(coverage.without_deadline_count, "tender")} without a deadline.
            </p>
          )}
        </>
      );
  }

  return (
    <section className="card coverage" aria-label="Coverage" aria-live="polite">
      {content}
    </section>
  );
}

function plural(count: number, noun: string): string {
  return `${count} ${count === 1 ? noun : `${noun}s`}`;
}

const BUCKETS: { key: keyof ClosingSoon; label: string }[] = [
  { key: "lt3", label: "Less than 3 days" },
  { key: "3to7", label: "3–7 days" },
  { key: "7to14", label: "7–14 days" },
];

// Ignores the period and "Open only": closing-soon tenders are open by definition.
function ClosingSoonSection() {
  const state = useLoad(getClosingSoon, []);

  const isEmpty =
    state.kind === "loaded" && BUCKETS.every(({ key }) => state.data[key].length === 0);

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
              <section key={key} className="closing-soon__bucket">
                <h3 className="closing-soon__title">
                  {label}{" "}
                  <span className="closing-soon__count">({state.data[key].length})</span>
                </h3>
                {state.data[key].length === 0 ? (
                  <p className="message">None.</p>
                ) : (
                  <TenderLinks tenders={state.data[key]} />
                )}
              </section>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

// Ignores the period: always the last 7 days.
function NewThisWeekSection({ openOnly }: { openOnly: boolean }) {
  const state = useLoad((signal) => getNewThisWeek({ openOnly }, signal), [openOnly]);

  return (
    <section className="section" aria-labelledby="new-this-week-title">
      <h2 id="new-this-week-title" className="section__title">
        New this week
      </h2>
      <div className="card">
        {state.kind === "loading" && <p className="message">Loading new tenders…</p>}
        {state.kind === "error" && (
          <p className="message message--error">
            Could not load new tenders. Check that the API is running and try again.
          </p>
        )}
        {state.kind === "loaded" && state.data.length === 0 && (
          <p className="message">
            {openOnly
              ? "No open tender was published in the last 7 days."
              : "No tender was published in the last 7 days."}
          </p>
        )}
        {state.kind === "loaded" && state.data.length > 0 && <TenderLinks tenders={state.data} />}
      </div>
    </section>
  );
}

type TenderLink = ClosingSoonTender | NewTender;

// Tenders as a list of links to their detail pages: object, reference and
// public buyer (and publication date when known), with the deadline's date
// over its time and the days left on the right.
function TenderLinks({ tenders }: { tenders: TenderLink[] }) {
  return (
    <ul className="tender-links">
      {tenders.map((tender) => (
        <li key={tender.id}>
          <Link to={`/tenders/${tender.id}`} className="tender-links__item">
            <span className="tender-links__main">
              <span className="tender-links__object">
                {tender.tender_object || "Untitled tender"}
              </span>
              <span className="tender-links__meta">
                Ref. {orDash(tender.reference_number)} · {orDash(tender.public_buyer)}
                {"publication_date" in tender &&
                  ` · Published ${formatDate(tender.publication_date)}`}
              </span>
            </span>
            <span className="tender-links__deadline">
              <Deadline value={tender.deadline} />
              <DaysLeft deadline={tender.deadline} />
            </span>
          </Link>
        </li>
      ))}
    </ul>
  );
}

// Tender counts per public buyer, category or location in the period, most
// first, as bars scaled to the largest count.
function TopSection({
  title,
  dimension,
  filter,
  empty,
  note,
}: {
  title: string;
  dimension: TopDimension;
  filter: InsightsFilter;
  empty: string;
  note?: string;
}) {
  const { period, openOnly } = filter;
  const state = useLoad(
    (signal) => getTop({ period, openOnly }, { dimension }, signal),
    [period, openOnly, dimension],
  );
  const titleId = `top-${dimension}-title`;
  const max = state.kind === "loaded" ? Math.max(1, ...state.data.map((v) => v.tender_count)) : 1;

  return (
    <section className="section" aria-labelledby={titleId}>
      <h2 id={titleId} className="section__title">
        {title}
      </h2>
      <div className="card">
        {state.kind === "loading" && <p className="message">Loading…</p>}
        {state.kind === "error" && (
          <p className="message message--error">
            Could not load {title.toLowerCase()}. Check that the API is running and try again.
          </p>
        )}
        {state.kind === "loaded" && state.data.length === 0 && (
          <p className="message">{empty}</p>
        )}
        {state.kind === "loaded" && state.data.length > 0 && (
          <ol className="bar-list">
            {state.data.map((value) => (
              <li key={value.label} className="bar-list__item">
                <span className="bar-list__label">{value.label}</span>
                <span className="bar-list__count">{value.tender_count}</span>
                <span className="bar-list__track" aria-hidden="true">
                  <span
                    className="bar-list__bar"
                    style={{ width: `${(value.tender_count / max) * 100}%` }}
                  />
                </span>
              </li>
            ))}
          </ol>
        )}
        {note && <p className="card__note">{note}</p>}
      </div>
    </section>
  );
}

const RESPONSE_WINDOW_DIMENSIONS: { value: ResponseWindowDimension; label: string }[] = [
  { value: "category", label: "By category" },
  { value: "public_buyer", label: "By public buyer" },
];

// The median response window per category or public buyer in the period,
// and the tenders whose window is under half their category's median.
function ResponseWindowSection({ filter }: { filter: InsightsFilter }) {
  const { period, openOnly } = filter;
  const [dimension, setDimension] = useState<ResponseWindowDimension>("category");
  const state = useLoad(
    (signal) => getResponseWindows({ period, openOnly }, dimension, signal),
    [period, openOnly, dimension],
  );
  const groupHeading = dimension === "category" ? "Category" : "Public buyer";

  return (
    <section className="section" aria-labelledby="response-window-title">
      <h2 id="response-window-title" className="section__title">
        Response window
      </h2>
      <div className="card">
        <div className="segmented" role="group" aria-label="Group response windows">
          {RESPONSE_WINDOW_DIMENSIONS.map(({ value, label }) => (
            <button
              key={value}
              type="button"
              className="filter-toggle"
              aria-pressed={dimension === value}
              onClick={() => setDimension(value)}
            >
              {label}
            </button>
          ))}
        </div>
        {state.kind === "loading" && <p className="message">Loading response windows…</p>}
        {state.kind === "error" && (
          <p className="message message--error">
            Could not load response windows. Check that the API is running and try again.
          </p>
        )}
        {state.kind === "loaded" && state.data.groups.length === 0 && (
          <p className="message">No tender in this period has a deadline.</p>
        )}
        {state.kind === "loaded" && state.data.groups.length > 0 && (
          <>
            <p className="message">
              Median days from publication to deadline. Tenders without a deadline are left out.
            </p>
            <div className="response-window__groups">
              <table className="insights-table">
                <thead>
                  <tr>
                    <th scope="col">{groupHeading}</th>
                    <th scope="col">Median</th>
                    <th scope="col">Tenders</th>
                  </tr>
                </thead>
                <tbody>
                  {state.data.groups.map((group) => (
                    <tr key={group.label}>
                      <td>{group.label}</td>
                      <td>{formatDays(group.median_days)}</td>
                      <td>{group.tender_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <h3 className="subsection__title">
              Short response windows{" "}
              <span className="subsection__count">
                ({state.data.short_response_windows.length})
              </span>
            </h3>
            <p className="message">Less than half the median for their category.</p>
            {state.data.short_response_windows.length === 0 ? (
              <p className="message">None.</p>
            ) : (
              <ul className="tender-links">
                {state.data.short_response_windows.map((tender) => (
                  <li key={tender.id}>
                    <Link to={`/tenders/${tender.id}`} className="tender-links__item">
                      <span className="tender-links__main">
                        <span className="tender-links__object">
                          {tender.tender_object || "Untitled tender"}
                        </span>
                        <span className="tender-links__meta">
                          Ref. {orDash(tender.reference_number)} · {orDash(tender.public_buyer)} ·{" "}
                          {tender.category}
                        </span>
                      </span>
                      <span className="tender-links__deadline">
                        <span className="response-window__short">
                          {formatDays(tender.response_window_days)}
                        </span>
                        <span className="tender-links__meta">
                          Median {formatDays(tender.category_median_days)}
                        </span>
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
      </div>
    </section>
  );
}

// "1 day", "12 days", "11.5 days".
function formatDays(days: number): string {
  return `${days} ${days === 1 ? "day" : "days"}`;
}
