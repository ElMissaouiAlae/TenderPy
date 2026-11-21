# 02: Tracer bullet: one UPLOADED tender with a single PDF reaches INDEXED

**What to build:** `python -m indexing --limit N` picks the first N tenders with status `UPLOADED`, downloads each DCE archive from S3 into a per-tender temp folder, extracts its DCE files (flat zip), chunks each with Docling `HybridChunker` (bge-m3 tokenizer, ~512 tokens), embeds the chunks with `BAAI/bge-m3` via sentence-transformers in batches, stores DCE files and chunks with citation metadata in pgvector on the existing Aiven database, and moves the tender `UPLOADED → CHUNKING → CHUNKED → EMBEDDING → INDEXED`. The temp folder is removed afterwards. Pipeline depends on `Embedder` and `VectorStore` interfaces. See spec and ADR 0001.

**Blocked by:** 01

**Status:** done

- [x] Alembic migration: `CREATE EXTENSION IF NOT EXISTS vector`; `dce_files` (tender FK, path within archive, file type, status, reason, created_at); `chunks` (dce_file FK cascade, chunk index, text, page numbers, heading path, `embedding_model`, `vector(1024)`, created_at); HNSW cosine index on embedding
- [x] Same migration (or a sibling) moves existing `INDEXED` tenders to `UPLOADED`; downgrade is defined
- [x] Every chunk stores tender, DCE file path, chunk index, page numbers, headings and the embedding model name
- [x] `--limit` respected; only `UPLOADED` tenders selected, in a deterministic order
- [x] Temp folder exists only while its tender is processed
- [x] Pipeline tests via `IndexingPipeline.run(limit)` with fake S3 client, fake deterministic 1024-dim embedder, in-memory vector store/repository, real Docling on a tiny PDF fixture
- [x] Opt-in slow test: real bge-m3 returns 1024-dim vectors
- [x] Integration test (integration_tests style) against Aiven: migration applied, extension present, insert + cosine search round-trip
