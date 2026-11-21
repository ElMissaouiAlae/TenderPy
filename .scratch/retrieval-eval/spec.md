# Spec: Retrieval evaluation and improvement loop (DeepEval)

Status: ready-for-agent

## Problem Statement

Retrieval returns search hits for a query, but nobody knows whether they are the *right* search hits. There is no dataset of queries with known answers, no score to compare one retrieval setup against another, and no record of why any retrieval setting was chosen. The answer-generation step is next, and if retrieval misses the evidence a generator needs, the generator cannot recover. Before building generation, the operator wants retrieval measured, improved over a fixed number of deliberate rounds, and either accepted or sent back for a second batch of work, while keeping the cost of LLM judging close to zero.

## Solution

A committed DeepEval eval suite for retrieval, run on demand with `deepeval test run`, separate from the unit tests. It scores scoped search hits for about 40 generated goldens drawn from the DCE files of 3–5 indexed tenders. Scoring happens at two levels:

- **Deterministic metrics** (free, repeatable): hit@1, hit@3, hit@5 and MRR against each golden's source chunk.
- **Judge metrics** (DeepEval's Contextual Precision, Contextual Recall, Contextual Relevancy): scored by `gpt-4o-mini` at the baseline and final round, and by free-tier Gemini in the rounds that need a judge.

After a baseline, 5 iteration rounds each change exactly one retrieval lever, rerun the eval, and keep or revert the change according to a fixed rule. Every round is recorded in a round log. After round 5, an exit gate decides between moving on to generation and running a second batch of rounds focused on re-indexing.

## User Stories

1. As an operator, I want a retrieval eval suite I can rerun without an agent, so that I can measure retrieval quality whenever I change something.
2. As an operator, I want the eval run only through `deepeval test run`, so that plain `pytest` never loads bge-m3, connects to the database, or spends API credits.
3. As an operator, I want the eval suite kept apart from the unit tests, so that the "no test loads the real bge-m3 model" rule still holds.
4. As an operator, I want goldens generated with `deepeval generate` from real DCE files, so that the dataset reflects the documents operators actually search.
5. As an operator, I want goldens drawn from 3–5 already-indexed tenders with varied organizations and file types, so that the dataset is not tuned to a single document.
6. As an operator, I want at least one tender with Arabic content included when one exists, so that Arabic retrieval is measured.
7. As an operator, I want about 40 goldens, so that scores are meaningful while each judged run stays cheap.
8. As an operator, I want to review and prune the generated goldens before the baseline, so that bad or ambiguous goldens do not distort every round.
9. As an operator, I want each golden tagged with its tender ID and organization acronym, so that it can be run scoped to its tender.
10. As an operator, I want every golden's query run scoped to its own tender, so that eval queries match how the UI will query and never see other tenders' chunks.
11. As an operator, I want the round log to record that unscoped (cross-tender) search is not evaluated, so that the gap is not forgotten.
12. As an operator, I want each golden mapped to the stored chunk it was generated from, so that retrieval can be scored without an LLM judge.
13. As an operator, I want goldens whose source passage cannot be mapped to a stored chunk dropped and counted, so that mapping errors do not silently lower scores.
14. As an operator, I want the mapping restricted to chunks of the golden's own tender, so that a golden is never credited against another tender's chunk.
15. As an operator, I want hit@1, hit@3 and hit@5 scored at fixed cutoffs whatever the retriever's top-k is, so that raising top-k cannot inflate the scores.
16. As an operator, I want MRR scored, so that I can see how high the source chunk is ranked, not just whether it was retrieved.
17. As an operator, I want deterministic metrics scored on every run at no API cost, so that rounds that do not need a judge cost nothing.
18. As an operator, I want Contextual Precision, Recall and Relevancy scored by an LLM judge, so that relevant chunks other than the source chunk are credited and noise is measured.
19. As an operator, I want each search hit passed to the judge as its heading path followed by its chunk text, so that the judge sees the same context a person reading the search hit would.
20. As an operator, I want `gpt-4o-mini` to judge the baseline and the final round, so that start and end scores come from one consistent, low-cost judge.
21. As an operator, I want free-tier Gemini to judge the top-k and threshold rounds, so that the rounds that need a judge cost nothing.
22. As an operator, I want one Gemini-judged baseline run, so that Gemini-judged rounds are compared against a Gemini-judged reference and never against `gpt-4o-mini` scores.
23. As an operator, I want judge thresholds fixed at 0.5 and never lowered, so that failures are fixed, not hidden.
24. As an operator, I want DeepEval's cache used on every run, so that goldens whose search hits did not change are not judged again.
25. As an operator, I want the judge's reasons kept, so that each round's lever can be picked from why goldens failed.
26. As an operator, I want each round to change exactly one lever, so that every score change can be attributed to it.
27. As an operator, I want the levers limited to those needing no re-index (top-k, similarity threshold, local reranker, hybrid search), so that rounds are fast and cheap.
28. As an operator, I want query expansion excluded, so that production queries never gain a per-query LLM cost.
29. As an operator, I want each round's lever chosen from the previous run's failures, so that rounds target real weaknesses.
30. As an operator, I want reranker and hybrid search rounds decided by hit@k and MRR, so that ranking changes are judged deterministically and for free.
31. As an operator, I want top-k and threshold rounds decided by the judge metrics, so that their noise-versus-coverage trade-off is actually measured.
32. As an operator, I want a judged change kept only if mean Contextual Recall is no more than 0.02 below the last kept round, the number of goldens passing Recall does not fall, and the mean of the three judge metrics rises, so that keep/revert decisions are not driven by judge noise or by averages that hide broken queries.
33. As an operator, I want a deterministic round's change kept only if no hit@k cutoff falls and MRR rises, so that ranking changes are kept only when they help.
34. As an operator, I want every comparison made against the last kept round, not simply the previous round, so that a reverted round never becomes the reference.
35. As an operator, I want reverted changes fully undone in code, so that the next round starts from the last kept state.
36. As an operator, I want a round log entry per round (lever, run identifier, judge used, per-metric scores against the last kept round, worst goldens, kept or reverted and why), so that I can see why the current retrieval setup was chosen.
37. As an operator, I want each kept round committed separately, so that any kept change can be traced and reverted on its own.
38. As an operator, I want the retrieval spec's Out of Scope section updated whenever a kept round adopts a lever it ruled out, so that the specs stay truthful.
39. As an operator, I want an exit gate after round 5 (mean Contextual Recall ≥ 0.8, or hit@5 ≥ 0.85, with no cluster of failing goldens), so that I know whether to build generation or improve retrieval further.
40. As an operator, I want a second batch of rounds proposed only when the judge's reasons point at chunking, so that re-index work is justified by evidence.
41. As an operator, I want the exit-gate targets adjustable after the baseline but never after a later round, so that targets are not moved to fit results.
42. As an operator, I want `OPENAI_API_KEY` and `GOOGLE_API_KEY` documented in the example environment file, so that the eval can be set up from the repo alone.
43. As a developer building generation, I want the eval structured so Faithfulness and Answer Relevancy can be added later, so that the full RAG pipeline can be evaluated with the same dataset.
44. As a developer, I want the deterministic metrics and the golden-to-chunk mapping unit-tested, so that the free keep/revert decisions rest on verified logic.

## Implementation Decisions

- **Scope**: retrieval only. Generation does not exist and is out of scope. The judge metrics are DeepEval's retriever metrics; generator metrics are added when generation exists.
- **New top-level eval package**, next to the integration tests (not under the unit tests), containing the eval suite, a separate metrics module (as the DeepEval skill requires) and the dataset file. Run only via `deepeval test run ... -c`.
- **No tracing and no Confident AI**: uses the DeepEval skill's no-tracing single-turn template. Each golden becomes a test case whose `retrieval_context` is the golden's search hits in rank order, one string per hit formatted as heading path plus chunk text. In docs, `retrieval_context` is described as "the query's search hits", consistent with the glossary (avoid "retrieved chunk").
- **Entry point**: the suite calls the existing `Retriever.retrieve(query, top_k, tender)`, built the same way the retrieval CLI builds it (same settings, embedder and vector store), with each golden's tender.
- **Dataset**: generated with `deepeval generate --method docs` from the DCE files of 3–5 indexed tenders, with styling flags matching an operator querying tender documents in French (and Arabic where present). About 40 goldens, reviewed and pruned by the operator. Each golden's metadata carries the tender ID, organization acronym and the passage it was generated from.
- **Golden-to-chunk mapping** (new seam): maps a golden's generated-from passage to the best-overlapping stored chunk of the same tender, above a cutoff. Unmapped goldens are dropped from the deterministic metrics and counted in the round log. Needed because DeepEval's generator chunks documents itself and its passages do not align with Docling chunks.
- **Deterministic metrics** (new seam): custom DeepEval metrics for hit@1, hit@3, hit@5 and MRR against the source chunk. Pure functions of a source chunk identity and a ranked list of search hits. Cutoffs are fixed and independent of the retriever's top-k.
- **Judge metrics**: Contextual Precision, Contextual Recall, Contextual Relevancy, threshold 0.5, reasons on.
- **Judges**: `gpt-4o-mini` for the baseline and final round; free-tier Gemini for top-k and threshold rounds, plus one Gemini baseline run as their reference. Scores from different judges are never compared. Switching judge provider is otherwise not allowed mid-loop.
- **Levers**: top-k, similarity threshold, local reranker (`BAAI/bge-reranker-v2-m3`, applied to a larger candidate set), hybrid search (Postgres full-text plus vector, merged with RRF; needs a migration but no re-embedding). Excluded: query expansion (per-query LLM cost), HNSW tuning and an exact scan for unscoped queries (no effect: scoped queries already use an exact scan), and every lever that needs a re-index (chunk size, embedding raw text instead of contextualized text, OCR).
- **Keep rules**: judged rounds keep a change if mean Contextual Recall ≥ last kept round − 0.02, the count of goldens passing Recall does not drop, and the mean of the three judge metrics rises. Deterministic rounds keep a change if no hit@k cutoff drops and MRR rises. The reference is always the last kept round; the baseline is the first kept round.
- **Round log**: one markdown log in this feature's scratch directory, one entry per round.
- **Exit gate** after round 5: move to generation if mean Contextual Recall ≥ 0.8 (final `gpt-4o-mini` run) or hit@5 ≥ 0.85, with no cluster of failing goldens. Otherwise, propose a re-index batch only if the judge's reasons point at chunking; if they point at the dataset, fix the dataset instead.
- **Dependencies and config**: `deepeval` in the dev dependency group; `OPENAI_API_KEY` and `GOOGLE_API_KEY` added to the example environment file.
- **Git**: one branch for the work; one commit for the eval suite and dataset, one commit per kept round; reverted rounds leave only their log entry.
- **Guardrails** (from the DeepEval skill): no hand-written goldens; difficult goldens are not deleted without a recorded reason; thresholds are never lowered; no change that overfits the goldens at the cost of general correctness.

## Testing Decisions

- Good tests check external behaviour (inputs in, scores or mappings out), never internals.
- **Seam 1, `Retriever.retrieve`**: existing seam, already unit-tested. The eval suite that calls it is not unit-tested; it is a thin wrapper run only through `deepeval test run`, as the indexing and retrieval CLIs are left untested.
- **Seam 2, deterministic metrics** (unit, in the unit tests): given a source chunk identity and a ranked list of search hits, cover the source chunk at rank 1, rank 3 and rank 5, beyond rank 5, absent, and an empty list. Check hit@1/3/5 and MRR values, and that the scores do not depend on how many hits were returned beyond the cutoff.
- **Seam 3, golden-to-chunk mapping** (unit, in the unit tests): cover an exact match, the best partial match above the cutoff, no match (golden reported as unmapped), and a better-matching chunk from another tender that must not be chosen.
- No unit test calls OpenAI or Gemini, connects to the database, or loads bge-m3 or the reranker.
- Each lever that changes retrieval code (threshold, reranker, hybrid search) gets tests at the existing `Retriever` and `PgVectorStore` seams, following `tests/test_retriever.py` and the vector-store integration tests.
- Prior art: `tests/test_retriever.py` and `tests/test_indexing_pipeline.py` (fake embedder and fake store), `integration_tests/vector_store_scoped_search.py`.

## Out of Scope

- Answer generation and the generator metrics (Faithfulness, Answer Relevancy).
- Evaluating unscoped (cross-tender) search.
- Levers that need a re-index: chunk size, embedding raw text instead of contextualized text, OCR. Deferred to a possible second batch after the exit gate.
- Query expansion and any per-query LLM call in production retrieval.
- HNSW tuning.
- Tracing, Confident AI and hosted reports.
- Running the eval in CI.
- More than 5 rounds in this batch.

## Further Notes

- Estimated API cost for the whole batch: about $0.50 (two `gpt-4o-mini` runs). Gemini-judged runs use the free tier and rely on caching to stay within its limits. If the free tier throttles a run so badly that it cannot complete, the round's judge is decided with the operator; scores from different judges are never compared.
- With one relevant chunk per golden, the deterministic metrics are stricter than reality and do not credit other chunks that answer the query. The judge metrics at the baseline and final round cross-check them.
- Eval vocabulary (golden, round, lever) is tooling vocabulary and is deliberately not added to `CONTEXT.md`, which is the tender-domain glossary.
- Builds on `.scratch/chunk-retrieval/spec.md`; that spec's Out of Scope section must be updated if a kept round adopts reranking, hybrid search or a similarity threshold.
