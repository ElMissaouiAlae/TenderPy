# 02: S3 upload capability

**What to build:** A `TenderUploader` class, shaped like the existing
`TenderDownloader`, that pushes a tender's downloaded DCE archive to S3 using
`boto3`. The S3 object key is derived deterministically from
`tender_id`/`organization_acronym`, mirroring how `TenderDownloader` builds
its download URL from the same two values. Bucket name and region are read
via `Settings.from_env()`, following the same env-var convention and
missing-value error handling already used for the database settings (e.g.
`DB_DATABASE_URL`).

**Blocked by:** None (can start immediately)

**Status:** done

- [x] `boto3` added as a project dependency
- [x] `Settings` (and `Settings.from_env()`) gains S3 bucket name and region fields, raising a clear error if a required one is missing, consistent with the existing `DB_DATABASE_URL` handling - validated lazily via `require_s3()` at the point of actual S3 use, so DB-only flows aren't forced to configure S3
- [x] `TenderUploader` is constructed with a tender's `tender_id`/`organization_acronym` (and an S3 client/config) and exposes a method to upload a local file
- [x] The S3 key used for an upload is deterministic and derived from `tender_id`/`organization_acronym`
- [x] Unit tests mock the S3 client (no real network/AWS calls), following `tests/test_downloader.py`'s pattern of mocking the single collaborator, and assert the client is called with the expected bucket/key/body
