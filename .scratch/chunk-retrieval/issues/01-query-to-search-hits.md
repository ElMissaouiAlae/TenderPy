# 01: Retrieve search hits for a query from the CLI, across all tenders or scoped to one

**What to build:** An operator runs `python -m retrieval "<query>" [--top-k N] [--tender ID --org ACRONYM]` and sees the top-k search hits (default 5) for their query, most similar first. The query is embedded with the same embedding model used for indexing, and only chunks embedded with that model are compared. Each search hit shows its rank, similarity (`1 − cosine distance`), tender ID, organization acronym, DCE file path, page numbers, heading path and full chunk text. Without `--tender`/`--org` the query runs across all tenders using the HNSW index. With them, it is scoped to that tender's chunks through an exact scan, so it returns k search hits whenever the tender has at least k chunks, even when other tenders' chunks are nearer the query. The logic sits in a `Retriever` (built from the existing `Embedder` and `VectorStore`) that the future generation step will call in-process. See `.scratch/chunk-retrieval/spec.md`.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] New `retrieval` package with a `Retriever` exposing `retrieve(query, top_k=5, tender=None) -> list[SearchHit]`, which embeds the query with its embedder and searches with the embedder's `model_name`; it imports `Embedder`, `VectorStore` and `SearchHit` from `indexing`
- [ ] `VectorStore.search` (protocol and `PgVectorStore`) accepts an optional `tender`; when given, results are restricted to that tender's chunks via an exact scan that does not depend on the planner choosing it
- [ ] Scoping to a tender that does not exist raises `RecordNotFoundError`; a tender with no chunks returns no search hits
- [ ] Chunks are searchable regardless of their tender's status (no filter on `INDEXED`); no similarity threshold is applied
- [ ] CLI reads embedding model, dimension and database from `Settings.from_env()` and closes the database on exit
- [ ] CLI rejects a blank or whitespace-only query, a `--top-k` below 1, and `--tender` without `--org` (or vice versa) as argparse errors, before loading the model
- [ ] CLI prints one human-readable block per search hit with rank, similarity, tender ID, organization acronym, DCE file path, pages, headings and full text
- [ ] CLI prints "No search hits" and exits 0 when nothing is returned; prints the error and exits non-zero for an unknown tender
- [ ] Unit tests for `Retriever.retrieve` with a deterministic fake embedder and a fake `VectorStore`: query embedded with the retriever's embedder; `model_name`, `top_k` and tender passed to the store; hits returned in store order; default top-k is 5; `RecordNotFoundError` propagates; empty store yields an empty list
- [ ] Integration test run by `python -m integration_tests` against real pgvector: with many other tenders' chunks stored (including ones nearer the query), a scoped query returns k hits from that tender only; an unscoped query returns nearest-first across tenders; an unknown tender raises `RecordNotFoundError`; a tender with no chunks returns an empty list; throwaway tenders and a dedicated embedding model name are cleaned up afterwards
- [ ] No test loads the real bge-m3 model; existing unit and integration tests still pass
- [ ] Manually verified: a French query against the already-indexed tenders prints sensible search hits, both unscoped and scoped to one tender
