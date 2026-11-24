# 05: Top public buyers, categories and locations, and response window

**What to build:** On the Insights page, a business user sees, for the selected period and open-only setting:
- **Top public buyers**, **top categories** and **top locations** by tender count. Names that differ only in case or spacing are counted together, and a note on the locations chart says only a tender's first location is counted.
- A **Response window** section with the median response window (in days) per category and per public buyer.
- A list of tenders with a **short response window** (less than half their category's median), each linking to its detail page.

See `.scratch/insights-dashboard/spec.md`.

**Blocked by:** 04 (shared period and open-only filters)

**Status:** ready-for-agent

- [ ] `GET /insights/top?dimension=public_buyer|category|location&limit=&period=&open_only=` returns values with counts, descending. Default limit 10, with an enforced maximum; an invalid dimension returns 422
- [ ] Grouping by public buyer and location trims, collapses internal whitespace and ignores case; the label is the most frequent original spelling. Tenders with no value for the dimension are left out
- [ ] `GET /insights/response-window?dimension=category|public_buyer&period=&open_only=` returns, per group, the median response window in whole days and the tender count, plus a list of short-response-window tenders (id, reference number, tender object, response window, category median)
- [ ] Response window = deadline date minus publication date, in days. Tenders missing either date are excluded, and tenders with no category are excluded from the short-window comparison
- [ ] The Insights page gains top public buyers, top categories, top locations (with the first-location-only note) and response window sections. Each has its own loading, empty and error states and responds to the period selector and open-only toggle
- [ ] Integration test against real Postgres with a fixed clock: counts and ordering, merging names that differ only in case or spacing, the label choice, the limit, medians with odd and even group sizes, the short-window threshold (just under vs exactly half the median), and the exclusions above
- [ ] Manually verified against real data
