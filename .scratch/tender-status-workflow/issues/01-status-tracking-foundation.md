# 01: Status tracking foundation

**What to build:** Extend `TenderStatus` to the full step sequence
(`DISCOVERED, DOWNLOADING, DOWNLOADED, UPLOADING, UPLOADED, INDEXED, FAILED`,
dropping the unused `PROCESSING`), add a nullable `last_status` column to
`TenderRecord` via a new Alembic migration, and give `TenderRepository` a
single method for writing status transitions after the initial insert. On a
failure transition, `status` becomes `FAILED` and `last_status` records the
last status the tender successfully reached; on any successful transition,
`last_status` is cleared back to null. Tenders are identified by their
existing natural key, `(tender_id, organization_acronym)`.

**Blocked by:** None (can start immediately)

**Status:** done

- [ ] `TenderStatus` enum contains exactly `DISCOVERED, DOWNLOADING, DOWNLOADED, UPLOADING, UPLOADED, INDEXED, FAILED` — `PROCESSING` is removed
- [ ] `TenderRecord` has a new nullable `last_status` column (same style as `status`), added via a new Alembic migration chained after the existing `001` revision
- [ ] `TenderRepository` exposes a method to update a tender's `status` (and optionally `last_status`), looked up by `(tender_id, organization_acronym)`
- [ ] Calling it with a new status and no `last_status` clears `last_status` back to null
- [ ] Calling it with `status=FAILED` and an explicit `last_status` sets both columns accordingly
- [ ] Integration test (against a real database, following the existing pattern used for `save`/`save_many`/`exists`) covers: a normal forward transition, a failure transition setting `FAILED` + a non-null `last_status`, and a subsequent successful transition clearing `last_status` back to null
