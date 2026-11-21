# 05: Idempotent re-index

**What to build:** Indexing a tender that already has DCE files and chunks replaces them atomically: existing `dce_files` (and their chunks) for that tender are deleted and the new set inserted in one transaction. Re-running never duplicates chunks, and a failure mid-write leaves the previous set intact.

**Blocked by:** 02

**Status:** done

- [x] Running the pipeline twice on the same tender yields the same DCE file and chunk counts as running once
- [x] Failure during the write leaves the tender's prior DCE files and chunks unchanged
- [x] Covered in pipeline tests (in-memory store honouring the replace contract) and in the Aiven integration test
