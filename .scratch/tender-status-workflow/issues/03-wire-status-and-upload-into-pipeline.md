# 03: Wire status tracking and S3 upload into the pipeline

**What to build:** Extend the date-range search flow so every discovered
tender's status is advanced through the real pipeline as it happens:
`DOWNLOADING` before the DCE archive fetch starts, `DOWNLOADED` once it's
written to local storage, `UPLOADING` before the S3 push starts, `UPLOADED`
once it succeeds, and `INDEXED` as the final step once everything else has
completed. If downloading or uploading a given tender's archive fails, that
tender's status becomes `FAILED` with `last_status` set to the last step it
completed successfully, and the run continues processing the remaining
tenders rather than aborting the whole batch.

**Blocked by:** 01 (status tracking foundation), 02 (S3 upload capability)

**Status:** ready-for-agent

- [ ] Each tender's status moves through `DOWNLOADING → DOWNLOADED → UPLOADING → UPLOADED → INDEXED` as the corresponding step actually happens, via the status-update method from ticket 01
- [ ] A failure downloading or uploading a tender's archive sets that tender's `status` to `FAILED` with `last_status` set to its last successfully completed step
- [ ] A failure on one tender does not stop the rest of the batch from being processed (matching the existing per-tender `try/except HttpRequestError` shape already used around download)
- [ ] After a successful download, the archive is uploaded to S3 via the `TenderUploader` from ticket 02
- [ ] Running the existing date-range-search integration test end to end shows tenders reaching `INDEXED` in the database (or `FAILED` with a `last_status` for any that errored)
