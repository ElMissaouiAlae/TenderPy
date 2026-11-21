# Spec: Chunk retrieval (query → top-k search hits)

Status: ready-for-agent

## Problem Statement

Tenders' DCE files are now chunked, embedded with `BAAI/bge-m3` and stored in pgvector, but nothing reads them back. There is no way to ask a question in natural language and see which chunks of which DCE files answer it. Without that retrieval step, the RAG system cannot be judged (are the right chunks coming back?) and the later generation step has nothing to build on. Users will often care about a single tender ("what is the submission deadline for this tender?"), and a query run across every tender would mix answers from unrelated tenders.

## Solution

A new retrieval command, run on demand from the CLI: `python -m retrieval "<query>" [--top-k 5] [--tender ID --org ACRONYM]`. It embeds the query with the same embedding model used for indexing, compares it with the stored chunks by cosine similarity, and prints the top-k search hits (default 5), each with its similarity score and citation (tender, organization, DCE file path, pages, headings) followed by the chunk's full text. By default the query runs across all tenders; passing a tender scopes it to that tender's chunks only, and a scoped query reliably returns k search hits whenever the tender has at least k chunks. The retrieval logic sits behind a `Retriever` that the future generation step will call directly.

## User Stories

1. As an operator, I want to run retrieval as a standalone command, so that I can query the indexed chunks without writing code.
2. As an operator, I want to pass my query as a free-text argument, so that I can ask questions in natural language.
3. As an operator, I want to ask queries in French or Arabic, so that I can search DCE files in the languages they are written in.
4. As an operator, I want the query embedded with the same embedding model used for indexing, so that the query and the chunks live in the same vector space.
5. As an operator, I want only chunks embedded with that same model to be compared, so that vectors from different models are never mixed.
6. As an operator, I want the 5 most similar chunks returned by default, so that I get a focused answer without configuring anything.
7. As an operator, I want to change the number of search hits with `--top-k`, so that I can look deeper when the top 5 are not enough.
8. As an operator, I want search hits ordered most similar first, so that the best evidence is at the top.
9. As an operator, I want each search hit to show its similarity score, so that I can judge how relevant it is and later pick a sensible threshold.
10. As an operator, I want each search hit to show its tender ID and organization acronym, so that I know which tender it comes from.
11. As an operator, I want each search hit to show its DCE file path inside the DCE archive, so that I can open the source file.
12. As an operator, I want each search hit to show its page numbers and heading path, so that I can find the exact location in the DCE file.
13. As an operator, I want each search hit's full chunk text printed, so that I can read the evidence without opening the file.
14. As an operator, I want to search across all tenders by default, so that I can find which tenders mention something.
15. As an operator, I want to scope a query to one tender with `--tender` and `--org`, so that answers do not mix unrelated tenders.
16. As an operator, I want both `--tender` and `--org` required together, so that a tender is always identified the same way as everywhere else in the system.
17. As an operator, I want a scoped query to return k search hits whenever the tender has at least k chunks, so that approximate search never silently drops my tender's chunks.
18. As an operator, I want unscoped queries to stay fast as the store grows, so that searching all tenders remains practical.
19. As an operator, I want a clear error and a non-zero exit when I scope to a tender that does not exist, so that a typo is not mistaken for "no relevant content".
20. As an operator, I want "No search hits" and a zero exit when the tender exists but has no chunks, or the store is empty, so that an empty answer is distinguishable from an error.
21. As an operator, I want a blank query rejected up front, so that I do not wait for the model to load just to get meaningless search hits.
22. As an operator, I want chunks searchable regardless of their tender's status, so that a tender whose re-index failed still serves its previously stored chunks.
23. As an operator, I want failed and skipped DCE files to simply contribute no chunks, so that one bad file never hides the rest of its tender.
24. As an operator, I want the embedding model and database taken from the same configuration as indexing, so that retrieval cannot drift from what was indexed.
25. As a developer building the generation step, I want a `Retriever` I can call in-process with a query, top-k and optional tender, so that I do not have to parse CLI output.
26. As a developer, I want the `Retriever` to depend on the existing `Embedder` and `VectorStore` interfaces, so that it can be tested with fakes and the store or model can be swapped as ADR 0001 intends.

## Implementation Decisions

- **New `retrieval` package**, separate from `indexing`, containing a `Retriever` and a `python -m retrieval` entry point. It imports `Embedder`, `VectorStore`, `PgVectorStore`, `SentenceTransformerEmbedder` and `SearchHit` from `indexing`; moving these into a shared package is deferred until a third consumer exists.
- **`Retriever`** is constructed with an `Embedder` and a `VectorStore` and exposes `retrieve(query, top_k=5, tender=None) -> list[SearchHit]`. It embeds the query with its embedder and calls `VectorStore.search` with the embedder's `model_name`, `top_k` as the limit, and the optional tender. No query prefix or instruction is added (bge-m3 does not need one); vectors are L2-normalised by the existing embedder exactly as chunks were.
- **`VectorStore.search` gains an optional `tender: Tender | None` argument** (the same identity type `replace_tender_files` takes; only `tender_id` and `organization_acronym` are used).
  - Without a tender: unchanged — cosine distance ordering served by the existing HNSW index, filtered to the embedding model.
  - With a tender: restricted to that tender's chunks and executed as an **exact scan** (the HNSW index must not be used), because pgvector's HNSW applies `WHERE` filters after the approximate candidate list (~40 rows by default) and would routinely return fewer than k hits for one tender among many. A tender's chunks number in the hundreds, so an exact scan is cheap. How the exact plan is forced is left to the implementer, but it must hold regardless of the planner's choice.
  - With a tender that does not exist: raises `RecordNotFoundError`, consistent with `replace_tender_files`.
- **Searchable set**: any chunk in the store, regardless of the tender's `status`. No filter on `INDEXED`. (Chunks are written atomically per tender, so stored chunks are always complete.)
- **No similarity threshold**: always return up to top-k search hits. Similarity is displayed as `1 − cosine distance`; `SearchHit` keeps carrying `distance`.
- **CLI** (`python -m retrieval`), following `indexing`'s entry point:
  - Positional `query`; blank or whitespace-only is an argparse error (checked before loading the model).
  - `--top-k`, integer, default 5, must be ≥ 1.
  - `--tender` and `--org` must be passed together; passing only one is an argparse error.
  - Builds `Settings.from_env()`, `Database`, `SentenceTransformerEmbedder(settings.embedding_model, settings.embedding_dim)`, `PgVectorStore`, then the `Retriever`; closes the database on exit.
  - Output: human-readable, one block per search hit with rank, similarity, tender ID and organization acronym, DCE file path, page numbers, heading path, then the full chunk text. No `--json`.
  - Empty result prints "No search hits" and exits 0. `RecordNotFoundError` prints the error and exits non-zero.
- **One-shot**: the model is loaded per invocation (a few seconds for bge-m3); no interactive loop.
- **No schema changes.** The existing HNSW cosine index and `dce_files.tender_record_id` index are sufficient.

## Testing Decisions

- Good tests exercise external behaviour through the seam (what goes in, which search hits come out, which errors are raised), never internals such as SQL text or how the exact scan is forced.
- **Seam 1 — `Retriever.retrieve`** (unit, `tests/`): driven with a deterministic fake embedder (as `FakeEmbedder` in the indexing pipeline tests) and a fake `VectorStore`. Covers: the query is embedded with the retriever's embedder; the embedder's `model_name`, `top_k` and tender are passed to the store; search hits are returned in store order; the default top-k is 5; `RecordNotFoundError` propagates for an unknown tender; an empty store yields an empty list. Prior art: `tests/test_indexing_pipeline.py`.
- **Seam 2 — `PgVectorStore.search`** (integration, `integration_tests/`, run via `python -m integration_tests`): against real Postgres with pgvector. Covers: a scoped query returns k search hits for a tender with ≥ k chunks while many other tenders' chunks are stored, including when those other chunks are all nearer the query than the tender's; a scoped query never returns another tender's chunks; an unscoped query still returns nearest-first across tenders; an unknown tender raises `RecordNotFoundError`; a tender with no chunks returns an empty list. Uses throwaway tenders and a dedicated embedding model name, cleaned up afterwards. Prior art: `integration_tests/vector_store_roundtrip.py`, `integration_tests/vector_store_replace.py`.
- **CLI is not tested**, consistent with `indexing`'s entry point; it is kept thin (argument parsing, wiring, printing, exit codes).
- No test loads the real bge-m3 model.

## Out of Scope

- Answer generation (the "G" in RAG) — the next step, which will call `Retriever` directly.
- A similarity threshold or relevance cutoff — to be chosen after observing real queries.
- Reranking, hybrid (keyword + vector) search, query expansion.
- `--json` or any machine-readable output.
- An interactive or long-running query loop, an HTTP API, or a UI.
- Moving `Embedder`, `VectorStore` and `SearchHit` out of `indexing` into a shared package.
- Filtering by tender status, organization alone, date or any field other than the tender identity.
- Tuning HNSW parameters (`ef_search`, `m`, `ef_construction`).

## Further Notes

- In production, tender scoping is expected to come from the UI (the user opens a tender, then asks), not from typing IDs; the CLI flags mirror that interaction for now.
- If a second embedding model is ever introduced alongside the first, the unscoped HNSW query has the same post-filtering issue for the `embedding_model` filter; with one model today every candidate passes it.
- Glossary terms used here (**Query**, **Search hit**) and the clarified meaning of `INDEXED` are in `CONTEXT.md`.
