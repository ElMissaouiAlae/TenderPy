Status: ready-for-agent

# Tender status tracking + S3 upload

## Problem Statement

A `Tender` moves through several steps between being discovered and being fully
processed — it gets saved, its DCE archive gets downloaded, and (not yet built)
that archive needs to be pushed to durable storage. Today the `TenderRecord`
row is written once with `status=DISCOVERED` and never updated again: nothing
in the codebase records whether a tender's DCE archive was actually downloaded,
whether it made it to S3, or whether any of that failed. If a run crashes or a
step errors partway through, there's no way to tell — by looking at the
database — which tenders still need work, or which step to resume from.

## Solution

Extend `TenderStatus` to cover every step a tender actually goes through
(`DISCOVERED → DOWNLOADING → DOWNLOADED → UPLOADING → UPLOADED → INDEXED`,
or `FAILED`), and make `TenderRepository` the single place that writes status
transitions as those steps happen. When a step fails, the tender's status
becomes `FAILED` and a new `last_status` field records the last step it
completed successfully, so a later run can resume from the right place instead
of restarting from scratch or guessing. Alongside this, add the S3 upload step
itself — a `TenderUploader` that pushes a downloaded DCE archive to S3 — and
wire both the download and upload steps into the existing date-range search
flow so status is kept accurate end to end.

## User Stories

1. As a developer inspecting the database, I want each tender's `status` to reflect exactly which step it has reached, so that I can tell discovered-but-not-downloaded tenders apart from fully-processed ones without reading logs.
2. As a developer inspecting the database, I want a tender's `status` to become `DOWNLOADING` before its DCE archive fetch starts, so that a crash mid-download is visible as "stuck downloading" rather than silently still looking like `DISCOVERED`.
3. As a developer inspecting the database, I want a tender's `status` to become `DOWNLOADED` only after its DCE archive is fully written to local storage, so that a partially-written file is never mistaken for a completed download.
4. As a developer inspecting the database, I want a tender's `status` to become `UPLOADING` before its DCE archive upload to S3 starts, so that I can tell "not yet attempted" apart from "in flight."
5. As a developer inspecting the database, I want a tender's `status` to become `UPLOADED` only after the S3 upload completes successfully, so that I know the archive is durably stored.
6. As a developer inspecting the database, I want a tender's `status` to become `INDEXED` as the final step, so that I have one unambiguous status value meaning "this tender is fully processed, nothing left to do."
7. As a developer running the pipeline, I want a tender's `status` to become `FAILED` if downloading its DCE archive raises an error, so that failures are visible in the database rather than only in logs.
8. As a developer running the pipeline, I want a tender's `status` to become `FAILED` if uploading its DCE archive to S3 raises an error, so that S3 failures are as visible as download failures.
9. As a developer running the pipeline, I want the tender's `last_status` to record the last step it completed successfully whenever it fails, so that I know exactly which step to retry from.
10. As a developer running the pipeline, I want `last_status` to be null for any tender that hasn't failed, so that I never mistake a stale value for something currently meaningful.
11. As a developer running the pipeline, I want `last_status` cleared back to null the moment a retry moves a `FAILED` tender forward again, so that the field never lingers as misleading history once the tender is healthy again.
12. As a developer, I want `TenderRepository` to expose a single method for changing a tender's status (and optionally its `last_status`), so that no other module ever writes to those columns directly or duplicates the SQL for it.
13. As a developer, I want the status-update method to identify the tender by `(tender_id, organization_acronym)` (its existing natural key), so that it's consistent with `TenderRepository.exists()` and the unique index already in place.
14. As a developer, I want a `TenderUploader` class shaped like the existing `TenderDownloader`, so that the S3 upload step is as easy to read, test, and reason about as the download step already is.
15. As a developer, I want S3 configuration (bucket name, region) loaded from environment variables using the same `Settings.from_env()` pattern as the database configuration, so that configuration stays centralized and consistent.
16. As a developer, I want the S3 object key for a tender's archive to be derived from `tender_id`/`organization_acronym`, so that uploaded objects can be located deterministically without a separate lookup table.
17. As a developer running `date_range_search.py`, I want each discovered tender to have its status advanced through `DOWNLOADING`/`DOWNLOADED`/`UPLOADING`/`UPLOADED`/`INDEXED` (or moved to `FAILED`) as the script actually performs those steps, so that the integration test reflects the real, current pipeline instead of only downloading to disk and stopping.
18. As a developer reading `persistence/models.py`, I want the obsolete `PROCESSING` status removed from the enum, so that the enum only contains steps the pipeline actually has.
19. As a developer running the existing Alembic migration chain, I want a new migration adding the `last_status` column (and covering the enum value change, since `status`/`last_status` are stored as `VARCHAR`), so that the schema stays in sync with the model without a manual `ALTER TABLE`.
20. As a developer writing tests, I want `TenderRepository`'s status-update method tested against a real database following the existing integration-test pattern (`integration_tests/`), so that its SQL/upsert behavior is verified the same way `save`/`save_many`/`exists` already are.
21. As a developer writing tests, I want `TenderUploader` tested with a mocked S3 client following the existing `test_downloader.py` pattern (mocking the collaborator, not real network calls), so that upload logic is verified without hitting real S3 in unit tests.
22. As a developer, I want a failure in one tender's download or upload step to not stop the whole `date_range_search.py` run, so that one bad tender doesn't prevent the rest of the batch from being processed (matching the existing per-tender `try/except HttpRequestError` around download today).

## Implementation Decisions

- **`TenderStatus` enum** (`persistence/models.py`): becomes `DISCOVERED, DOWNLOADING, DOWNLOADED, UPLOADING, UPLOADED, INDEXED, FAILED`. `PROCESSING` is removed — nothing implements it and no future step maps to it under this design.
- **`TenderRecord.last_status`**: new nullable `VARCHAR` column, same width/style as `status`. Holds a `TenderStatus` value or null. Only ever non-null while `status == FAILED`; represents the last status the tender successfully reached before the failing step began.
- **`TenderRepository` gets one new method**, something like `update_status(tender_id, organization_acronym, status, last_status=None)`, which is the only path by which `status`/`last_status` are ever written after the initial insert. It looks the row up by the existing `(tender_id, organization_acronym)` unique index (same identity `exists()` uses) and updates both columns (plus `updated_at`) in one statement.
  - On success at any step: call with the new `status`, `last_status=None` (clearing it, per user story 11).
  - On failure at any step: call with `status=FAILED`, `last_status=<the tender's current status before this step's attempt>` (i.e. the last status it actually reached).
- **`TenderUploader`** (new module, mirrors `downloader.py`'s `TenderDownloader` shape): constructed with an S3 client and the tender's `tender_id`/`organization_acronym`; exposes an `upload(local_path)`-style method that pushes the local DCE archive to the configured bucket under a deterministic key derived from `tender_id`/`organization_acronym` (mirroring how `TenderDownloader.download_url` is built from the same two values). Uses `boto3` — no existing S3 dependency or precedent in this repo, and no other library is favored by prior art, so this is a net-new choice.
- **S3 configuration**: extend `persistence/config.py`'s `Settings`/`Settings.from_env()` with S3 bucket name and region, following the existing `DB_*` env-var naming convention (e.g. `S3_BUCKET_NAME`, `S3_REGION`) and the same "raise a clear error if a required var is missing" pattern used for `DB_DATABASE_URL`.
- **Migration**: a new Alembic revision (chained after `001`) adding the `last_status` column. Since `status`/`last_status` are plain `VARCHAR`, no enum-type migration is needed at the database level — only the application-level `TenderStatus` Python enum changes.
- **Wiring into `date_range_search.py`**: the per-tender loop that currently only calls `TenderDownloader` and writes the zip to disk is extended to call `repository.update_status(...)` around each step (before/after download, before/after upload) and to construct/call `TenderUploader` after a successful download, following the same per-tender `try/except` shape already used for download failures.

## Testing Decisions

- Only external behavior is tested, not internal call sequencing — e.g. for `TenderRepository.update_status`, assert the resulting row's `status`/`last_status` in the database, not that a particular SQL statement was constructed.
- `TenderRepository.update_status`: tested via the real-database integration-test pattern already used for `save`/`save_many`/`exists` in `integration_tests/`. Covers: normal forward transitions, a failure transition setting `FAILED` + a non-null `last_status`, and a subsequent successful transition clearing `last_status` back to null.
- `TenderUploader`: unit-tested with a mocked S3 client, following `tests/test_downloader.py`'s pattern of mocking the single collaborator (there `HttpClient`, here the S3 client) and asserting the client was called with the expected bucket/key/body — no real network or AWS calls in this suite.
- `TenderStatus` enum change (removal of `PROCESSING`, new values): covered incidentally by the above tests exercising the new values; no separate test needed for the enum itself.
- `date_range_search.py` wiring: exercised as part of the existing integration test's manual/CI run (it already runs against a real Postgres and real HTTP session); no new automated assertions are required beyond what the existing test already checks (records present, archives downloaded), though the log output should reflect the new upload step succeeding or failing per tender.

## Out of Scope

- Automatic retry of `FAILED` tenders (a scheduler/worker polling for failed records). This spec only makes retrying *possible* by recording `last_status`; the retry mechanism itself is future work.
- Detecting or handling a tender's DCE archive changing after it's already been uploaded to S3 (replacing/versioning the S3 object). Tracked separately as `.scratch/tender-status-workflow/issues/01-s3-archive-replacement.md`.
- Tracking individual files inside a DCE archive as separate entities/statuses. The archive remains a single 1:1 artifact per tender.
- Any status/step beyond `INDEXED` (e.g. actual document parsing/search indexing behavior) — `INDEXED` is only the terminal marker that processing is complete, not a new feature to build.

## Further Notes

- `CONTEXT.md` already documents the resolved `TenderStatus`/`last_status` vocabulary from the design discussion that produced this spec — implementers should keep terminology consistent with it (e.g. "DCE archive," not "document").
- The natural key used throughout (`tender_id` + `organization_acronym`) is the same one `TenderRepository.exists()` and the unique index (`ix_tender_records_tender_id_org_acronym`) already use; no new identifier scheme is introduced.
