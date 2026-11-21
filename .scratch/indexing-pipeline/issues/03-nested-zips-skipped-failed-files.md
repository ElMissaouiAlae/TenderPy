# 03: Nested zips, skipped and failed DCE files

**What to build:** Archives containing nested zips are extracted recursively, with each DCE file's path recording where it came from inside the archive. DCE files Docling does not support are recorded `skipped` with a reason; DCE files that Docling fails to convert are recorded `failed` with the error. Neither stops the tender, which still reaches `INDEXED` with chunks from the good files.

**Blocked by:** 02

**Status:** done

- [x] Nested zip contents (including zips within zips) are extracted and chunked; recorded path shows the nesting
- [x] Unsupported file (e.g. `.dwg` fixture) → DCE file `skipped`, reason recorded, no chunks
- [x] Corrupt PDF fixture → DCE file `failed`, error recorded, no chunks
- [x] Tender with a mix of good, skipped and failed files ends `INDEXED`
- [x] Tested through `IndexingPipeline.run` with fixtures built in the test
