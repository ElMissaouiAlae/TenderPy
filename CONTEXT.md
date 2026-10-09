# Tender Crawler

Discovers public tenders, downloads their DCE (Dossier de Consultation des Entreprises) archive, uploads that archive to durable storage, and records the result against a `TenderRecord`.

## Language

**Tender**:
A single procurement opportunity discovered from the source platform, identified by `(tender_id, organization_acronym)`.

**DCE archive**:
The single zip file containing a tender's consultation documents, fetched via `TenderDownloader`. One archive per tender (1:1) — there is currently no concept of tracking the individual files inside it separately.
_Avoid_: document (ambiguous between "the archive" and "a file inside it" — always say "DCE archive" for the former)

**DCE file**:
A single file extracted from a DCE archive (including files found inside nested zips). Belongs to exactly one tender. The unit that gets chunked.
_Avoid_: document, attachment

**Chunk**:
A contiguous piece of a DCE file's text, carrying enough metadata (tender, DCE file, location within the file) to be cited back to its source. Chunks are only persisted once embedded.

**Query**:
The free-text question a user searches the indexed chunks with. Embedded with the same model as the chunks it is compared against.

**Search hit**:
A chunk returned for a query, carrying its citation (tender, DCE file, pages, headings) and its similarity score. A query can be scoped to a single tender or run across all tenders.
_Avoid_: result, match, retrieved chunk, document

**Status**:
The current step a tender's processing has reached, stored on `TenderRecord.status` (`TenderStatus` enum): `DISCOVERED → DOWNLOADING → UPLOADED → CHUNKING → CHUNKED → EMBEDDING → INDEXED`, or `FAILED` if any step errors.

- `DISCOVERED`: the tender row exists — written immediately when the tender is found, before download starts.
- `DOWNLOADING` / `UPLOADED`: fetching the DCE archive and saving it to document storage (S3), in one step.
- `CHUNKING` / `CHUNKED`: splitting the tender's DCE files into chunks.
- `EMBEDDING`: embedding chunks and storing them in the vector store.
- `INDEXED`: the terminal state — the tender's latest chunks are embedded and stored. Searchability does not depend on status: any chunk in the store can be returned as a search hit, including chunks of a tender that later failed a re-index.
- `FAILED`: a step errored; see **Last status** below for how resume works.

**Last status**:
`TenderRecord.last_status` — nullable field that, only while `status = FAILED`, holds the last status the tender *successfully* completed (e.g. `UPLOADED` means "resume from indexing"). Cleared back to null the moment a retry starts moving the tender forward again. Has no meaning when `status != FAILED`.
