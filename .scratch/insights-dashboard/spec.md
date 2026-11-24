# Spec: Insights dashboard and typed tender dates

Status: ready-for-agent

## Problem Statement

TenderPy is being repositioned from a tool for collecting tenders into a tool that helps businesses decide which tenders to bid on. Today, it can't do that.

- **Dates are hard to read and impossible to reason about.** The publication date and the deadline are stored as text exactly as the source platform shows it (`"15/01/2026"`, `"20/10/2026 11:00"`). In the UI, the deadline's date and time run together on one line. Since they're text, nothing can be sorted, filtered or counted by date. "Which tenders close this week?" has no answer.
- **There is no market view.** A business can't see which public buyers publish the most, which categories and locations are active, or how much time buyers usually give to prepare a bid. That is exactly what decides whether a tender is worth pursuing.
- **Tenders are hidden for the wrong reason.** The tender list and detail pages only show tenders whose DCE archive has been downloaded. For a decision tool, that hides relevant tenders: one closing in two days is invisible if its download failed or hasn't run yet.

## Solution

1. **Typed dates.** The **publication date** is stored as a calendar date. The **deadline** is stored as a timezone-aware timestamp in Moroccan local time (Africa/Casablanca). New tenders are parsed when discovered, and existing rows are backfilled. Everywhere the UI shows a deadline, the date and the time appear on separate lines. "Tender end date" is renamed **Deadline** throughout.
2. **Every discovered tender is visible.** The tender list and detail pages show every discovered tender, not just those with a DCE archive. The "Download DCE archive" button appears only when the tender has one.
3. **Closing soon on the list.** Each open tender in the list has a days-left badge, and a "Closing soon" filter restricts the list to tenders closing within the next 14 days.
4. **An Insights page.** A new sidebar entry, "Insights", gives a market-wide view (it isn't personalised to any business) with:
   - **Closing soon:** open tenders grouped as less than 3 days, 3–7 days and 7–14 days left, each with its countdown, linking to the tender.
   - **New this week:** tenders published in the last 7 days.
   - **Top public buyers, top categories, top locations:** tender counts over the selected period.
   - **Response window:** the median response window per category and per public buyer, with **short response windows** highlighted.
   - **Coverage:** "Based on N tenders published between X and Y", plus "N tenders without a deadline" when there are any.
   - **Period selector:** 7 days, 30 days (the default), 90 days and all time, never extending beyond the data we have. An "Open only" toggle restricts the counts to open tenders.

## User Stories

1. As a business user, I want each tender's deadline date and time shown on separate lines, so that I can read when it closes at a glance.
2. As a business user, I want the publication date shown as a date only, so that I don't see a meaningless time.
3. As a business user, I want deadlines shown in Moroccan local time, so that they match what the source platform says.
4. As a business user, I want the same deadline shown wherever I look (list, detail, Insights), so that I never see contradictory values.
5. As a business user, I want the word "Deadline" used consistently, so that I'm not unsure whether "end date" means something else.
6. As a business user, I want every discovered tender in the tender list, so that I don't miss opportunities just because their documents haven't been downloaded yet.
7. As a business user, I want to open the detail page of any discovered tender, so that I can see its details even before its DCE archive is available.
8. As a business user, I want the "Download DCE archive" button only when an archive exists, so that I never click a download that fails.
9. As a business user, I want a days-left badge on each open tender in the list, so that I can see how much time remains without doing the arithmetic.
10. As a business user, I want closed tenders to show no countdown, so that I don't mistake them for opportunities.
11. As a business user, I want a "Closing soon" filter on the tender list, so that I can focus on tenders that need action within 14 days.
12. As a business user, I want the closing-soon list ordered by nearest deadline first, so that the most urgent tender is at the top.
13. As a business user, I want an "Insights" entry in the sidebar, so that the market view is always one click away.
14. As a business user, I want Insights to show open tenders grouped as less than 3 days, 3–7 days and 7–14 days left, so that I can triage by urgency.
15. As a business user, I want each closing-soon entry to show reference number, tender object, public buyer and the deadline's date and time, so that I can recognise it without opening it.
16. As a business user, I want each closing-soon entry to link to the tender's detail page, so that I can act on it directly.
17. As a business user, I want a "New this week" section, so that I can catch tenders published in the last 7 days.
18. As a business user, I want to see which public buyers published the most tenders in the period, so that I know which buyers are worth building a relationship with.
19. As a business user, I want public buyer names that differ only in case or spacing counted as one, so that one buyer's volume isn't split.
20. As a business user, I want to see which categories have the most tenders in the period, so that I know where demand is.
21. As a business user, I want to see which locations have the most tenders in the period, so that I can judge whether I can operate there.
22. As a business user, I want a note on the locations chart saying that only a tender's first location is counted, so that I don't over-trust the numbers for multi-location tenders.
23. As a business user, I want the median response window per category, so that I know how much time I usually get to prepare a bid in my sector.
24. As a business user, I want the median response window per public buyer, so that I know which buyers give tight deadlines.
25. As a business user, I want tenders with a short response window (under half their category's median) highlighted, so that I'm warned that preparing a bid will be rushed.
26. As a business user, I want to choose the period as 7 days, 30 days, 90 days or all time, so that I can compare recent activity with the longer-term pattern.
27. As a business user, I want 30 days selected by default, so that the page is useful without configuration.
28. As a business user, I want an "Open only" toggle on the counts, so that I can see the market I can still bid on versus everything published.
29. As a business user, I want to see how many tenders the numbers are based on and the date range they cover, so that I know how far to trust them.
30. As a business user, I want periods never to extend beyond the data we have, so that "all time" doesn't imply coverage we don't have.
31. As a business user, I want to see how many tenders have no deadline, so that I know some tenders are missing from the deadline-based figures.
32. As a business user, I want loading, empty and error states on every Insights section, so that one failing section doesn't blank the whole page.
33. As an operator, I want existing tenders' dates converted automatically during the migration, so that historical data is immediately usable in Insights.
34. As an operator, I want any date the migration can't read logged and left empty instead of failing the migration, so that one malformed row doesn't block a deploy.
35. As an operator, I want newly discovered tenders stored with typed dates from the start, so that no later backfill is needed.
36. As a developer, I want Insights served by a small set of read-only endpoints, so that the UI never computes aggregates itself.
37. As a developer, I want the current time injected into deadline-based calculations, so that closing-soon and period results are deterministic in tests.
38. As a future product owner, I want Insights queries structured so that a business-profile filter (sectors, regions) can be added later, so that personalised insights don't require a rewrite.

## Implementation Decisions

**Dates**
- The domain `Tender` carries the publication date as a calendar date and the deadline as a timezone-aware datetime (Africa/Casablanca). The parser converts the platform text into these types. A deadline with no time is treated as end of day. Text that can't be read becomes `None`, and the parser logs it but never raises.
- One shared function converts platform date text into these types. Both the parser and the backfill migration use it, so their rules can't diverge.
- Schema: `publication_date` becomes a date column. `tender_end_date` is renamed `deadline` and becomes a timezone-aware timestamp column. Both are indexed. The Alembic migration converts existing text in place, sets unreadable values to null and logs each one with the tender's id.
- `tender_end_date` is renamed `deadline` across the domain model, ORM model, mapper, lookup, API responses and UI client.
- The API sends the deadline as an ISO 8601 datetime with its offset, and the publication date as an ISO date. The UI formats them: the deadline's date on one line and its time (HH:mm, Moroccan local time) on the next. The UI does not convert to the browser's timezone.

**Visibility**
- The tender lookup stops filtering by "has a DCE archive". The list and detail pages return every discovered tender. Each response includes a boolean `has_dce_archive`, computed with the existing persistence rule. The download endpoint keeps returning 404 when there is no archive.
- The definition of "has a DCE archive" in `CONTEXT.md` stays the same. It no longer decides which tenders are visible.

**Tender list**
- `GET /tenders` gains an optional closing-soon filter: open tenders whose deadline is within the next 14 days, ordered by nearest deadline. Without the filter, ordering stays newest publication first, then id.
- Summaries include the deadline. The UI computes the days-left badge from it and shows no badge for closed tenders or tenders without a deadline.

**Insights API**
- A new read-only **insights** module in persistence answers aggregate questions with SQL against tender records. It takes "now" as a parameter and never reads the clock itself. The API layer gets "now" from an injected clock, so tests can fix it.
- Endpoints, all read-only and all accepting `period` (`7d`, `30d`, `90d` or `all`, default `30d`) and `open_only` (boolean, default false) unless noted:
  - `GET /insights/coverage`: total tender count, earliest and latest publication date, and the count without a deadline.
  - `GET /insights/closing-soon`: open tenders closing within 14 days, grouped into `lt3`, `3to7` and `7to14` buckets. Each item has id, reference number, tender object, public buyer and deadline. Ignores `period` and `open_only`.
  - `GET /insights/new-this-week`: tenders published in the last 7 days, newest first. Ignores `period`.
  - `GET /insights/top?dimension=public_buyer|category|location&limit=`: counts per value, descending. Default limit 10, with an enforced maximum.
  - `GET /insights/response-window?dimension=category|public_buyer`: the median response window in days per group, with tender counts, plus a list of tenders with a short response window (id, reference number, response window, category median).
- A period is based on publication date, and always means the last N days up to "now", intersected with the range covered by the data.
- Grouping by public buyer and location trims the name, collapses internal whitespace and ignores case. The label shown is the most frequent original spelling.
- Location means the single location the parser stores (the first one shown on the platform).
- **Response window** = deadline date minus publication date, in whole days. Tenders without either date are excluded from response-window figures.
- **Short response window** = less than half the median response window of tenders in the same category over the same period. Tenders with no category are excluded from the comparison.
- Everything is computed on request. Precomputing is deferred until it becomes measurably slow.
- Each query builds its filters (period, open only) in one shared place, so a later business-profile filter (categories, locations) can be added once and apply everywhere.

**UI**
- The sidebar gains an "Insights" entry. The Insights page has independent sections (coverage banner, closing soon, new this week, top public buyers, top categories, top locations, response window). Each section loads separately and has its own loading, empty and error states.
- The period selector and "Open only" toggle sit at the top of the page and apply to the sections that accept them.
- The tender list gains the days-left badge and the "Closing soon" filter. The detail page shows the deadline as date over time and hides the download button when `has_dce_archive` is false.
- All API calls go through the existing typed API client.

**Glossary**
- `CONTEXT.md` already defines Publication date, Deadline, Open tender, Response window, Short response window, Closing soon, Public buyer and Organisation. Code and UI use those terms.

## Testing Decisions

- Good tests exercise external behaviour only: given tenders as the platform shows them or as stored rows, assert what a user or API client gets back. They don't assert SQL shape, internal function calls or intermediate data structures.
- **Seam 1: Parser (unit, existing).** Extend the parser tests to cover publication dates (`DD/MM/YYYY`), deadlines with a time (`DD/MM/YYYY HH:mm`, including the multi-line form with `<br>`), deadlines without a time (end of day), timezone (Africa/Casablanca), and unreadable text (`None` with no exception). Prior art: the existing parser tests and their HTML fixtures.
- **Seam 2: HTTP API against real Postgres (integration, existing pattern).** Insert tender records with a unique test organisation, build the app with the real lookup and insights module and a fixed clock, call the endpoints through the FastAPI test client, assert on the JSON, and clean up the rows. Cover:
  - list and detail return tenders in every status, with the correct `has_dce_archive`
  - the closing-soon filter on `/tenders`
  - closing-soon buckets at their boundaries (exactly 3, 7 and 14 days left, and already closed)
  - new this week
  - top counts, including merging names that differ only in case or spacing
  - periods capped to the data's coverage, and `open_only`
  - medians and short response windows
  - tenders without a deadline counted in coverage and excluded elsewhere
  Prior art: the integration test for the tender lookup and its siblings.
- The migration's backfill reuses the same date-parsing function as seam 1, so it isn't tested separately beyond a manual run against a copy of real data.
- The existing in-memory unit tests for the API are updated for the renamed field and the removed archive filter. They are not extended to cover insights: an in-memory fake would reimplement the SQL logic and prove nothing.
- There are no frontend tests, since the project has none today.

## Out of Scope

- Business profiles, accounts, saved searches and personalised "matches for you".
- Grouping by organisation (the parent body). Counts in v1 are by public buyer only.
- Fetching every location of a multi-location tender.
- Volume trends over time, buyer seasonality, procurement type mix and keyword trends in the tender object. These need several months of crawled history.
- Anything extracted from the DCE archive (estimated budget, bid bond, required qualifications, go/no-go checklists). That comes with the RAG work.
- Scheduling the crawler or backfilling historical tenders from the platform.
- Precomputed or cached aggregates.
- Notifications or alerts for closing tenders.

## Further Notes

- How useful Insights is depends on crawl coverage, and there's no scheduler in the repo. The coverage banner exists so users aren't misled. Setting up regular crawls is the next lever on data quality.
- Tickets are in `issues/`: 01 typed dates and 02 every tender visible (both can start immediately), then 03 closing soon (blocked by 01 and 02), then 04 coverage, period and new this week (blocked by 03), then 05 top counts and response window (blocked by 04).
- The `ui-dashboard` spec's rule that "tenders without a DCE archive are not listed" is deliberately reversed here.
