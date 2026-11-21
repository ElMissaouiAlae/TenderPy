# 08: Round 4

**What to build:** One lever change, chosen from the failures of the last run and the judge's reasons, scored and kept or reverted. Levers: top-k, similarity threshold, local reranker (`BAAI/bge-reranker-v2-m3`), hybrid search (Postgres full-text plus vector, merged with RRF). Exactly one lever per round. Reranker and hybrid search rounds are decided by the fixed-cutoff metrics: keep if no hit@k drops and MRR rises. Top-k and threshold rounds are decided by the Gemini judge, against the Gemini reference: keep if mean Contextual Recall ≥ last kept − 0.02, the count of goldens passing Recall does not drop, and the mean of the three judge metrics rises. Always compare against the last kept round. See `.scratch/retrieval-eval/spec.md`.

**Blocked by:** 07.

**Status:** ready-for-agent

- [ ] The lever is chosen from cited failing goldens and judge reasons, recorded in the round log before the change is made.
- [ ] Any retrieval code change has tests at the `Retriever` or `PgVectorStore` seam (prior art: `tests/test_retriever.py`, `integration_tests/vector_store_scoped_search.py`).
- [ ] The eval is run with the cache on and a round identifier.
- [ ] The round log entry has the lever, the judge (if any), per-metric scores against the last kept round, worst goldens, and the keep/revert decision with its reason.
- [ ] If kept, the change is committed on its own. If reverted, the code is back to the last kept state and only the log entry remains.
- [ ] No threshold is lowered, no golden is removed without a recorded reason, and the judge provider is not switched.
