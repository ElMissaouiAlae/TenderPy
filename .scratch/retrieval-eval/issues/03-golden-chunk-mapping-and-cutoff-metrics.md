# 03: Golden-to-chunk mapping and fixed-cutoff metrics

**What to build:** Each reviewed golden can be scored without an LLM judge. A mapping links each golden's generated-from passage to the best-overlapping stored chunk of the same tender, above a cutoff. Goldens that cannot be mapped are reported, not guessed. Custom DeepEval metrics score hit@1, hit@3, hit@5 and MRR for a ranked list of search hits against the golden's source chunk, at fixed cutoffs whatever the retriever's top-k.

**Blocked by:** 02 (Review and prune the goldens).

**Status:** ready-for-agent

- [ ] Unit tests for the mapping cover an exact match, the best partial match above the cutoff, no match (golden reported as unmapped), and a better-matching chunk from another tender that is never chosen.
- [ ] Unit tests for the metrics cover the source chunk at rank 1, 3 and 5, beyond rank 5, absent, and an empty list. They also check that scores do not change with the number of hits returned beyond the cutoff.
- [ ] No unit test calls an API, connects to the database or loads a model.
- [ ] Running the mapping over the reviewed dataset records the number of mapped and unmapped goldens, per tender, in the round log.
