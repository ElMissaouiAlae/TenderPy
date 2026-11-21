# Spec: Indexing pipeline (DCE archive → chunks → pgvector)

Status: ready-for-agent

## Problem Statement

Tenders' DCE archives are discovered, downloaded and uploaded to S3, but their contents are opaque: nothing inside a DCE archive can be searched or retrieved. To build a RAG system over tenders, every DCE file inside each archive needs to be split into chunks, embedded, and stored in a vector store with enough metadata to cite each chunk back to its tender, file and location. The DCE files are mostly French with some Arabic, archives often contain nested zips and unsupported file types, and the work must be trialled on a small batch (5 tenders) before running over everything.

## Solution

A new indexing pipeline, run on demand as its own command with a batch limit (e.g. `--limit 5`). It picks the first N tenders with status `UPLOADED`, downloads each DCE archive from S3 into a per-tender temporary folder, extracts every DCE file (recursing into nested zips), chunks each supported DCE file with Docling's hybrid chunker, embeds the chunks with `BAAI/bge-m3`, and stores DCE files and chunks (with embeddings and citation metadata) in pgvector on the existing Aiven Postgres. The tender's status advances `UPLOADED → CHUNKING → CHUNKED → EMBEDDING → INDEXED`. A single bad DCE file never fails the tender; only tender-level errors do, and those are resumable through `last_status`.

## User Stories

1. As an operator, I want to run indexing as a standalone command, so that I can test it without running a crawl.
2. As an operator, I want to pass a batch limit, so that I can index just 5 tenders first and scale up after reviewing the results.
3. As an operator, I want the batch to be the first N tenders with status `UPLOADED`, so that selection is predictable and repeatable.
4. As an operator, I want each tender's DCE archive downloaded from the configured S3 bucket, so that indexing works from durable storage rather than local leftovers.
5. As an operator, I want each tender processed in its own temporary folder, so that tenders never mix files.
6. As an operator, I want the temporary folder deleted when a tender finishes, whether it succeeded or failed, so that disk usage stays bounded on large batches.
7. As an operator, I want nested zips inside a DCE archive to be opened recursively, so that no DCE file is missed.
8. As an operator, I want every extracted DCE file recorded, including ones that could not be chunked, so that I can see exactly what was in each archive.
9. As an operator, I want DCE files of types Docling does not support (images, drawings, signatures, etc.) marked `skipped` with a reason, so that I know why they produced no chunks.
10. As an operator, I want a DCE file that crashes Docling marked `failed` with the error, so that one corrupt PDF does not block the rest of the tender.
11. As an operator, I want the tender still marked `INDEXED` when some of its DCE files were skipped or failed, so that partial content is searchable.
12. As an operator, I want a tender marked `FAILED` only for tender-level errors (S3 download failure, unreadable archive, database error), so that `FAILED` means "needs attention".
13. As an operator, I want `last_status` set to the last status the tender completed when it fails, so that a retry knows where it stopped.
14. As an operator, I want the tender's status to move through `CHUNKING`, `CHUNKED`, `EMBEDDING`, `INDEXED`, so that I can see progress and diagnose where tenders get stuck.
15. As an operator, I want re-indexing a tender to replace its previous DCE files and chunks atomically, so that retries never produce duplicate chunks.
16. As an operator, I want a per-tender and per-batch summary logged (DCE files found, chunked, skipped, failed, chunk count), so that I can judge the 5-tender trial.
17. As a RAG developer, I want each chunk to carry its tender, DCE file path within the archive, chunk index, page numbers and section headings, so that answers can cite "tender X › CPS.pdf › p.12 › Article 5".
18. As a RAG developer, I want chunks sized for retrieval (~512 tokens measured with the embedding model's own tokenizer), so that chunks fit the model and retrieve precisely.
19. As a RAG developer, I want French and Arabic text embedded with a strong multilingual model (`BAAI/bge-m3`), so that retrieval works across both languages.
20. As a RAG developer, I want every chunk to record which embedding model produced it, so that a future model change can re-embed alongside existing vectors without mixing them.
21. As a RAG developer, I want an approximate nearest-neighbour index on embeddings using cosine distance, so that similarity search stays fast as the corpus grows.
22. As a RAG developer, I want vector reads and writes to go through a `VectorStore` interface, so that the store can be swapped without touching the pipeline.
23. As a developer, I want the embedding model name and dimension read from configuration, so that changing models is a config change plus a migration, not a code change.
24. As a developer, I want the pgvector extension and new tables created by Alembic migrations, so that schema setup is reproducible on Aiven.
25. As a developer, I want existing tenders currently marked `INDEXED` (set by the old flow right after upload) moved back to `UPLOADED` by a migration, so that they get indexed for real.
26. As a developer, I want the discovery/download/upload flow to stop at `UPLOADED`, so that `INDEXED` only ever means "chunks embedded and searchable".
27. As a developer, I want embeddings computed in batches, so that CPU memory stays bounded on large DCE files.
28. As a developer, I want the prototype chunking and embedding scripts folded into the new package and removed, so that there is one implementation.

## Implementation Decisions

- **New package `indexing`**, split by job, mirroring the existing `discovery` / `persistence` / `core` layout:
  - **Extractor**: given a DCE archive (bytes or path) and a working directory, yields DCE files with their path inside the archive, recursing into nested zips. Unreadable top-level archive is a tender-level error.
  - **Chunker**: wraps Docling `DocumentConverter` + `HybridChunker` configured with the bge-m3 tokenizer and ~512-token max. Input: a DCE file. Output: chunks with text, chunk index, page numbers and heading path. Distinguishes "unsupported type" (→ skipped) from "conversion error" (→ failed). OCR disabled for now.
  - **Embedder** interface: `embed(texts) -> list of vectors`. Production implementation uses sentence-transformers with the model named by `EMBEDDING_MODEL`, batched.
  - **VectorStore** interface: replace all DCE files and chunks for a tender in one transaction; search (for later RAG use). Production implementation on Postgres + pgvector.
  - **IndexingPipeline**: orchestrates selection, per-tender status transitions, temp-dir lifecycle, per-file error isolation and tender-level failure handling. Entry point `run(limit)`.
  - **Command**: `python -m indexing --limit N`.
- **S3 read**: the existing S3 storage provider gains a load operation (it currently only saves); the pipeline depends on the storage interface, not boto3 directly. The S3 client stays injectable as today.
- **Status model**: `TenderStatus` gains `CHUNKING`, `CHUNKED`, `EMBEDDING`. Flow: `UPLOADED → CHUNKING → CHUNKED → EMBEDDING → INDEXED`, or `FAILED` with `last_status` = last completed status. `last_status` cleared when a retry starts moving the tender forward (existing rule in `CONTEXT.md`).
- **Retry semantics**: a `FAILED` tender whose `last_status` is `UPLOADED` or later is eligible for indexing; since storage is replaced atomically per tender, indexing always restarts from download for that tender (no partially persisted chunks to resume from).
- **Schema** (Alembic, on the existing Aiven Postgres 18 / pgvector 0.8.6):
  - `CREATE EXTENSION IF NOT EXISTS vector`.
  - `dce_files`: id, tender record FK, path within archive, file type/extension, status (`chunked` | `skipped` | `failed`), error/skip reason, created_at.
  - `chunks`: id, dce_file FK (cascade delete), chunk index, text, page numbers, heading path, `embedding_model`, `embedding vector(EMBEDDING_DIM=1024)`, created_at.
  - HNSW index on `chunks.embedding` with cosine ops.
  - Data migration: tenders with status `INDEXED` → `UPLOADED`.
- **Write transaction**: per tender, delete existing `dce_files` (cascading to chunks) and insert the new set in one transaction, then set `INDEXED`.
- **Configuration**: `Settings` gains `EMBEDDING_MODEL` (default `BAAI/bge-m3`) and `EMBEDDING_DIM` (default 1024). Vector store uses the existing `DB_URL`.
- **Orchestrator change**: the existing download/upload flow ends at `UPLOADED` instead of setting `INDEXED`.
- **Dependencies**: add `sentence-transformers` and `pgvector` (SQLAlchemy type); `docling` already added.
- **Model choice** recorded in ADR 0001 (bge-m3 + pgvector on Aiven, with the three reversibility measures).

## Testing Decisions

- Good tests assert externally observable behaviour only: tender statuses and `last_status`, DCE file records and their statuses/reasons, chunks and their metadata, temp-dir cleanup, idempotency on re-run. They do not assert on internal calls or Docling internals.
- **Primary seam: `IndexingPipeline.run(limit)`**, with fakes injected for:
  - S3 — a fake client returning zip bytes built in the test (same injection pattern as `S3DocumentStorage` tests).
  - Embedder — deterministic fake returning 1024-dim vectors.
  - VectorStore and tender repository — in-memory fakes.
  - Docling runs for real on tiny fixtures: small PDF, small DOCX, a nested zip, an unsupported file (e.g. `.dwg`), a corrupt PDF.
- Scenarios: limit respected and only `UPLOADED` tenders picked; happy path reaches `INDEXED` with expected chunk metadata; nested zip files extracted; unsupported file `skipped`; corrupt file `failed` while tender still `INDEXED`; S3 failure and bad archive → `FAILED` with correct `last_status`; temp dir removed on success and failure; re-run replaces rather than duplicates.
- Opt-in slow test loading real bge-m3 to check dimension and that the model name is recorded.
- Integration test in the `integration_tests/` style against the real Aiven database: migrations apply, extension present, round-trip insert + cosine search on a few chunks.
- Prior art: `tests/test_file_storage.py` (injected S3 client), `tests/test_orchestrator.py` (orchestrator with mocked collaborators), `integration_tests/status_transitions.py`.

## Out of Scope

- Wiring indexing into the crawl run automatically.
- RAG query/answer layer (beyond the `VectorStore` search method).
- OCR for scanned PDFs.
- Parallel or distributed processing of tenders.
- Re-embedding tooling for a future model change (enabled by `embedding_model`, not built now).
- Indexing beyond the trial batch until the 5-tender run is reviewed.

## Further Notes

- Glossary terms used: **Tender**, **DCE archive**, **DCE file**, **Chunk**, **Status**, **Last status** — see `CONTEXT.md`.
- bge-m3 is ~570M params and slow on CPU; acceptable for the trial, revisit if full-corpus throughput is a problem.
- `.scratch/` is gitignored, so this spec is local-only.
