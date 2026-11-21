# 04: Eval suite and baselines

**What to build:** The operator can run `deepeval test run -c` on the retrieval eval suite and get baseline scores. The suite lives in a top-level eval package next to the integration tests, uses the DeepEval skill's no-tracing template, and keeps its metrics in a separate module. For each golden it calls `Retriever.retrieve` scoped to the golden's tender, and passes the search hits as `retrieval_context`, one string per hit formatted as heading path plus chunk text. Three baselines are run: fixed-cutoff metrics, the `gpt-4o-mini` judge (Contextual Precision, Recall, Relevancy, threshold 0.5, reasons on) and the free-tier Gemini judge.

**Blocked by:** 03 (Golden-to-chunk mapping and fixed-cutoff metrics).

**Status:** ready-for-agent

- [ ] Plain `pytest` does not collect the eval suite.
- [ ] Every golden runs scoped to its own tender.
- [ ] The judge model is chosen per run without code edits.
- [ ] The round log has a baseline entry with all three runs' per-metric scores, pass counts, worst goldens, run identifiers and cost.
- [ ] The round log records that unscoped (cross-tender) search is not evaluated.
- [ ] The suite and baseline entry are committed.
