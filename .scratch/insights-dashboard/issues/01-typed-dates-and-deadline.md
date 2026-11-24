# 01: Typed dates and Deadline

**What to build:** A business user opening the tender list or a tender's detail page sees the **deadline** as its date on one line and its time (Moroccan local time) on the line below, and the **publication date** as a date only. Behind that, both dates are stored as real types: the publication date as a calendar date, and the deadline as a timezone-aware timestamp in Africa/Casablanca. Newly discovered tenders are parsed when the crawler finds them, and existing rows are converted by the migration. "Tender end date" is renamed **Deadline** throughout. See `.scratch/insights-dashboard/spec.md`.

**Blocked by:** None (can start immediately)

**Status:** ready-for-human

- [x] One shared function turns platform date text into typed values: `DD/MM/YYYY` gives a date; `DD/MM/YYYY HH:mm` (including the multi-line `<br>` form) gives an Africa/Casablanca datetime; a deadline without a time means end of day; unreadable text gives `None`, logged, never raised
- [x] The parser and the domain `Tender` use the typed values; `tender_end_date` is renamed `deadline` in the domain model, ORM model, mapper, lookup, API responses and UI client
- [x] Alembic migration: `publication_date` becomes a date column, `tender_end_date` is renamed `deadline` and becomes a timezone-aware timestamp column, both indexed; existing text is converted with the shared function, and unreadable values are set to null and logged with the record id
- [x] The migration has a working downgrade (converting back to the platform's text format)
- [x] The API sends `deadline` as ISO 8601 with its offset and `publication_date` as an ISO date
- [x] List and detail pages show the deadline's date over its time (HH:mm, Moroccan local time, not the browser's timezone), the publication date as a date only, and the label "Deadline"
- [x] Parser tests cover every format above, including the unreadable case and timezone
- [x] Existing unit and integration tests are updated for the rename and the new types
- [ ] Manually verified: migration run against the real database with a count of nulled values reported, and the UI shows the split date and time

## Comments

**Implementation (agent):** all code boxes are done; only the manual verification is left for a human.

- **Migration rehearsed, not applied.** The upgrade and downgrade ran against the real database inside one transaction that was rolled back: 3808 tender records converted, **0 publication dates and 0 deadlines nulled**, and the downgrade gave back every original value (the deadline text now has a space between date and time). The agent was not permitted to run `alembic upgrade head` itself. To finish: run `uv run alembic upgrade head` (it logs the nulled count), then check the list and detail pages show the deadline's date over its time.
- **Stored deadlines had no separator.** Every existing row read like `04/11/202610:00`: the parser had joined the `<br>`-split text with nothing between. `core/dates.py` reads that form too, and the parser now joins with a space.
- **Don't convert to Africa/Casablanca in SQL.** The Aiven Postgres timezone data puts Casablanca at UTC+0 in October 2026; Python's (correctly) says UTC+1. Deadlines are stored as exact instants computed in Python, and `core.dates.in_moroccan_time` converts them back in Python. Tickets 03–05 should compare against "now" as an instant, and should not use `AT TIME ZONE 'Africa/Casablanca'` (e.g. for the response window's deadline date). Compute those in Python or with a parameter computed in Python.
- **End of day is 23:59.** It's stored in minutes, like the platform's times, so the downgrade writes it back unchanged.
- **Publication-date text that isn't date-shaped isn't logged.** The parser finds the publication date by scanning the cell's bare `<div>`s for a `DD/MM/YYYY` shape, so a non-matching `<div>` is other content, not an unreadable date. Only date-shaped but invalid text (e.g. `31/02/2026`) is logged.
