# 04: Tender-level failure and retry

**What to build:** Tender-level errors (S3 download fails, top-level archive unreadable, database error) mark the tender `FAILED` with `last_status` set to the last status it completed, without stopping the rest of the batch. The temp folder is removed on failure too. `FAILED` tenders whose `last_status` is `UPLOADED` or later are eligible for the next indexing run; `last_status` is cleared when the retry starts moving the tender forward (per `CONTEXT.md`).

**Blocked by:** 02

**Status:** done

- [x] S3 failure → `FAILED`, `last_status = UPLOADED`
- [x] Bad top-level archive → `FAILED`, with correct `last_status`
- [x] Database failure while storing → `FAILED`, no partial chunks persisted for that tender
- [x] Other tenders in the same batch still process
- [x] Temp folder removed after a failed tender
- [x] Eligible `FAILED` tenders are selected on the next run and `last_status` is cleared when retried
- [x] Tested through `IndexingPipeline.run` with failing fakes
