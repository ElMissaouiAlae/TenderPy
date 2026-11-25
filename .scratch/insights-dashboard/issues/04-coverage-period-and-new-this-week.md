# 04: Coverage, period selector, open-only toggle and New this week

**What to build:** At the top of the Insights page, a business user sees "Based on N tenders published between X and Y", plus "N tenders without a deadline" when there are any. They can choose the period (7 days, 30 days by default, 90 days, all time) and toggle "Open only"; both apply to the period-aware sections. A "New this week" section lists tenders published in the last 7 days, newest first, linking to their detail pages. See `.scratch/insights-dashboard/spec.md`.

**Blocked by:** 03 (the Insights page, insights module and clock)

**Status:** ready-for-human

- [x] Period and open-only filtering is built in one shared place in the insights module, so a later business-profile filter can be added there once
- [x] A period is based on publication date: the last N days up to "now", intersected with the range the data covers. `all` means the full coverage range
- [x] `GET /insights/coverage?period=&open_only=` returns the tender count, the earliest and latest publication date, and the count without a deadline
- [x] `GET /insights/new-this-week` returns tenders published in the last 7 days, newest first (id, reference number, tender object, public buyer, publication date, deadline)
- [x] Invalid `period` values are rejected with 422
- [x] The Insights page has a period selector (default 30 days) and an "Open only" toggle. The coverage banner and the "New this week" section each have their own loading, empty and error states
- [x] Integration test against real Postgres with a fixed clock: coverage for each period, a period capped to the data's range, `open_only`, the count without a deadline, and the "New this week" boundary (exactly 7 days ago)
- [ ] Manually verified against real data

## Comments

**Implementation (agent):** every code box is done. Only the manual browser check is left for a human, so Status is `ready-for-human` (as for 03).

- **Checked against real data through the API only.** On 2026-11-24 the real database's newest publication date was 2026-10-10. So `7d` and `30d` are empty, and New this week is empty: that is correct, and those sections will show their empty states. `90d` and `all` both cover 3808 tenders from 2026-09-13 to 2026-10-10: the 90-day period is capped to the data. With `open_only`, 90d has 8 open tenders. `period=1y` returns 422. The browser extension wasn't connected. To finish: run `python -m api` and `npm run dev`, open Insights, and try each period and "Open only". Running a crawl first would give 7d/30d and New this week something to show.
- **Period boundary.** "Last N days" means the N calendar days ending today (Moroccan date). A tender published exactly N days ago is outside the period, so exactly 7 days ago is not New this week. Recorded in `CONTEXT.md` (Period, Coverage, New this week).
- **Coverage range.** The range is the earliest and latest publication date among the tenders counted. That caps it to the data. With "Open only", it is the range of the open tenders.
- **Without a deadline ignores "Open only".** A tender with no deadline is never open. Counting it only among open tenders would always give 0 and hide the warning, so it is counted over the whole period.
- **Shared filter.** `persistence.insights.InsightsFilter` builds the period and open-only conditions. Coverage and New this week use it (New this week with the period fixed to 7 days). Closing soon ignores both, per the spec, so it doesn't use it yet. When a business-profile filter lands, closing soon must be routed through `InsightsFilter` too.
- **Also changed:** the period and "Open only" are kept in the URL (`?period=7d&open_only=1`). The closing-soon list markup is now a shared `TenderLinks` list, also used by New this week (CSS `.closing-soon__list/item/...` became `.tender-links__*`). New this week items show their publication date.
- **Review follow-ups not done (judgement calls):** the tender-item fields are repeated across `ClosingSoonTender`/`NewTender` and their response models; `new_this_week` takes a bare `open_only` rather than an `InsightsFilter`, because it ignores the period; there is no limit on New this week.
