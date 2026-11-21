# 01: Generate the golden dataset

**What to build:** The operator gets a dataset of about 40 goldens drawn from real DCE files, ready for review. DeepEval goes in the dev dependency group, and `OPENAI_API_KEY` and `GOOGLE_API_KEY` are added to the example environment file. Pick 3–5 indexed tenders with varied organizations and file types, including one with Arabic content if one exists. Fetch their DCE files and generate goldens with `deepeval generate --method docs`, using styling flags for an operator querying tender documents in French (and Arabic where present). Use `gpt-4o-mini` for generation. See `.scratch/retrieval-eval/spec.md`.

**Blocked by:** None (can start immediately).

**Status:** needs-info

- [x] DeepEval is in the dev dependency group; plain `pytest` still passes and does not import it.
- [x] The example environment file documents `OPENAI_API_KEY` and `GOOGLE_API_KEY`.
- [x] The chosen tenders, and why they were chosen, are recorded in the round log (`.scratch/retrieval-eval/rounds.md`).
- [ ] About 40 goldens are written to the eval package's dataset file; none are hand-written.
- [ ] Each golden carries its tender ID, organization acronym and the passage it was generated from.
- [ ] Goldens in Arabic are present if any chosen tender has Arabic content; otherwise the round log says none exists.
- [ ] Generation cost is noted in the round log.

## Comments

### 2026-10-14: blocked on generation model

**Done (uncommitted):** deepeval synced in the dev group; `addopts = "-p no:deepeval"` added to pytest config, because deepeval auto-registers a pytest plugin (`deepeval test run` passes `-p deepeval`, which re-enables it). Plain `pytest` passes without importing deepeval. `.env.example` documents both keys. The chosen tenders and the generate command are in `rounds.md`.

**Blocked:** the OpenAI key in `.env` (also the replacement key) returns `insufficient_quota` / `credit_balance_exhausted`. deepeval hides this and only reports "No synthetic goldens found". Check with a one-line `curl` to `/v1/embeddings` before retrying.

`--method docs` needs two models: an LLM to write the goldens and an **embedding model** to build contexts. Gemini can be the LLM (`deepeval set-gemini`), but the deepeval CLI has no Gemini embedder (only OpenAI, Azure, Ollama, or a local OpenAI-compatible server).

**Decision needed (operator):**
- **Fund OpenAI:** run as specified (`gpt-4o-mini`).
- **A:** Gemini LLM + Ollama embeddings (`deepeval set-ollama-embeddings`, e.g. `nomic-embed-text`), still `--method docs`. Spec unchanged apart from the generation model.
- **B:** Gemini LLM + `--method contexts` built from stored Docling chunks. No embeddings needed, and the source passage is the stored chunk, so mapping (issue 03) becomes near-exact. This departs from the spec's `--method docs`, so the spec must be updated.

Either Gemini option needs `GOOGLE_API_KEY` in `.env`, and the round log must record the generation model actually used.
