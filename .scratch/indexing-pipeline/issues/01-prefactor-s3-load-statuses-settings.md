# 01: Prefactor: S3 archive load, new statuses, embedding settings

**What to build:** Make the indexing work easy to add without changing current behaviour. The S3 document storage can load a DCE archive by key (not only save). `TenderStatus` gains `CHUNKING`, `CHUNKED`, `EMBEDDING`. Settings expose `EMBEDDING_MODEL` (default `BAAI/bge-m3`) and `EMBEDDING_DIM` (default 1024), read from env. See spec `.scratch/indexing-pipeline/spec.md` and ADR 0001.

**Blocked by:** None (can start immediately)

**Status:** done

- [x] S3 storage loads an object's bytes from the configured bucket; tested with an injected fake client, like the existing save tests
- [x] Loading without a configured bucket raises `ConfigurationError`
- [x] Storage interface exposes loading so the pipeline does not depend on boto3
- [x] `TenderStatus` includes `CHUNKING`, `CHUNKED`, `EMBEDDING`; existing values unchanged
- [x] Settings read `EMBEDDING_MODEL` / `EMBEDDING_DIM` with the defaults above; config tests cover defaults and overrides
- [x] Existing test suite passes unchanged
