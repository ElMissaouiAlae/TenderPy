# 05: Top public buyers, categories and locations, and response window

**What to build:** On the Insights page, a business user sees, for the selected period and open-only setting:
- **Top public buyers**, **top categories** and **top locations** by tender count. Names that differ only in case or spacing are counted together, and a note on the locations chart says only a tender's first location is counted.
- A **Response window** section with the median response window (in days) per category and per public buyer.
- A list of tenders with a **short response window** (less than half their category's median), each linking to its detail page.

See `.scratch/insights-dashboard/spec.md`.

**Blocked by:** 04 (shared period and open-only filters)

**Status:** ready-for-human

- [x] `GET /insights/top?dimension=public_buyer|category|location&limit=&period=&open_only=` returns values with counts, descending. Default limit 10, with an enforced maximum; an invalid dimension returns 422
- [x] Grouping by public buyer and location trims, collapses internal whitespace and ignores case; the label is the most frequent original spelling. Tenders with no value for the dimension are left out
- [x] `GET /insights/response-window?dimension=category|public_buyer&period=&open_only=` returns, per group, the median response window in whole days and the tender count, plus a list of short-response-window tenders (id, reference number, tender object, response window, category median)
- [x] Response window = deadline date minus publication date, in days. Tenders missing either date are excluded, and tenders with no category are excluded from the short-window comparison
- [x] The Insights page gains top public buyers, top categories, top locations (with the first-location-only note) and response window sections. Each has its own loading, empty and error states and responds to the period selector and open-only toggle
- [x] Integration test against real Postgres with a fixed clock: counts and ordering, merging names that differ only in case or spacing, the label choice, the limit, medians with odd and even group sizes, the short-window threshold (just under vs exactly half the median), and the exclusions above
- [ ] Manually verified against real data

## Comments

**Implementation (agent):** every code box is done. Only the manual browser check is left for a human, so Status is `ready-for-human` (as for 03 and 04).

- **Checked against real data through the API only.** With today's clock (2026-11-24), `90d` top counts give Travaux 1468 / Services 1359 / Fournitures 981, top locations RABAT 284, MAROC 260, …, and top public buyers headed by ONEE – Branche Eau (89). `30d` is empty (newest publication is 2026-10-10). All-time response windows: medians 22–23 days per category, ~1,200 public-buyer groups, 87 short response windows. Each endpoint answers in under 1.5 s. To finish: run `python -m api` and `npm run dev`, open Insights, try each period, "Open only", the "By category / By public buyer" toggle, and a short-window link.
- **Median is not rounded.** Response windows are whole days, but the median of an even-sized group is the mean of the middle two, so it can end in .5 (e.g. 11.5 days). The ticket says "in whole days"; I read that as the unit. If medians should be whole numbers, the change is one line in `_median_by_key` (and the test's 9.5/11.5 expectations). Recorded in `CONTEXT.md` (Response window).
- **Label and ties.** The label is the most frequent spelling after trimming and collapsing whitespace (case kept). Ties between values are broken by label; `/top` sorts labels in Postgres, response-window groups in Python, so accented labels could tie-break differently on the two endpoints.
- **Category is normalised too**, the same way as public buyer and location (one shared dimension→column map and normalisation in `persistence/insights.py`). Harmless for the platform's fixed category names.
- **Open only applies to the short-window baseline**: the category median is computed over the same tenders, so a tender's "short" flag can change with the toggle ("over the same period" and same filter).
- **Extra fields on short-window items:** `public_buyer` and `category`, shown in the UI list.
- **UI:** the three top sections sit side by side as bar lists; the response-window section has a "By category / By public buyer" toggle (one table at a time, scrolling inside the card) and the short-window list below it. Top limit: default 10, maximum 50.
- **Not done (judgement calls from review):** negative response windows (deadline before publication) are kept; there are none in the real data. No cap on response-window groups or the short list. The integration tests' client/status helpers aren't shared across test files. The "most frequent spelling" rule exists once in SQL (`/top`) and once in Python (response windows, which need the deadline's Moroccan date).

