# 06: Summary logging, 5-tender trial run, remove prototypes

**What to build:** Each tender and each batch logs a summary (DCE files found / chunked / skipped / failed, chunk count, duration). Run `python -m indexing --limit 5` against the real S3 bucket and Aiven database, review chunk quality and timings, and record findings as a comment on this ticket. Remove the prototype `document_chunker.py` and `embeddings.py` now that the `indexing` package replaces them.

**Blocked by:** 03, 04, 05

**Status:** ready-for-human

- [ ] Per-tender and per-batch summaries logged
- [ ] Trial run on 5 real tenders completed; results (counts, timings, sample chunks, issues) appended under `## Comments`
- [ ] Prototype scripts deleted; nothing imports them
- [ ] Decision noted on whether to scale up the batch
