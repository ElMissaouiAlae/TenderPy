# 01: Typed dates and Deadline

**What to build:** A business user opening the tender list or a tender's detail page sees the **deadline** as its date on one line and its time (Moroccan local time) on the line below, and the **publication date** as a date only. Behind that, both dates are stored as real types: the publication date as a calendar date, and the deadline as a timezone-aware timestamp in Africa/Casablanca. Newly discovered tenders are parsed when the crawler finds them, and existing rows are converted by the migration. "Tender end date" is renamed **Deadline** throughout. See `.scratch/insights-dashboard/spec.md`.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] One shared function turns platform date text into typed values: `DD/MM/YYYY` gives a date; `DD/MM/YYYY HH:mm` (including the multi-line `<br>` form) gives an Africa/Casablanca datetime; a deadline without a time means end of day; unreadable text gives `None`, logged, never raised
- [ ] The parser and the domain `Tender` use the typed values; `tender_end_date` is renamed `deadline` in the domain model, ORM model, mapper, lookup, API responses and UI client
- [ ] Alembic migration: `publication_date` becomes a date column, `tender_end_date` is renamed `deadline` and becomes a timezone-aware timestamp column, both indexed; existing text is converted with the shared function, and unreadable values are set to null and logged with the record id
- [ ] The migration has a working downgrade (converting back to the platform's text format)
- [ ] The API sends `deadline` as ISO 8601 with its offset and `publication_date` as an ISO date
- [ ] List and detail pages show the deadline's date over its time (HH:mm, Moroccan local time, not the browser's timezone), the publication date as a date only, and the label "Deadline"
- [ ] Parser tests cover every format above, including the unreadable case and timezone
- [ ] Existing unit and integration tests are updated for the rename and the new types
- [ ] Manually verified: migration run against the real database with a count of nulled values reported, and the UI shows the split date and time
