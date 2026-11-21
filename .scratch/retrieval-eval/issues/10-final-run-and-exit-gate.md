# 10: Final judged run and exit gate

**What to build:** The operator gets a verdict on whether retrieval is ready for generation. Run the `gpt-4o-mini` judge and the fixed-cutoff metrics on the final kept setup, and compare them with the `gpt-4o-mini` baseline. Apply the exit gate: move on to generation if mean Contextual Recall ≥ 0.8 or hit@5 ≥ 0.85, with no cluster of failing goldens. Otherwise, propose a re-index batch only if the judge's reasons point at chunking; if they point at the dataset, propose fixing the dataset instead.

**Blocked by:** 09 (Round 5).

**Status:** ready-for-agent

- [ ] The final run's scores sit next to the baseline in the round log, with cost.
- [ ] The exit-gate verdict is recorded with the evidence behind it.
- [ ] `.scratch/chunk-retrieval/spec.md` Out of Scope is updated for any kept lever it ruled out (reranking, hybrid search, similarity threshold).
- [ ] The round log ends with a total batch cost.
