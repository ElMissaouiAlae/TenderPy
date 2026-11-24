# Tender Crawler

Discovers public tenders, downloads their DCE (Dossier de Consultation des Entreprises) archive, uploads that archive to durable storage, and records the result against a `TenderRecord`.

## Language

**Tender**:
A single procurement opportunity discovered from the source platform, identified by `(tender_id, organization_acronym)`.

**Publication date**:
The calendar day the tender appeared on the source platform. A date only, with no time of day.

**Deadline**:
The date and time (Moroccan local time, Africa/Casablanca) at which bid submissions for a tender close.
_Avoid_: end date, tender end date, clôture

**Open tender**:
A tender whose deadline is still in the future. Once the deadline passes, the tender is **closed**. This has nothing to do with processing **Status**.

**Response window**:
The number of days between a tender's publication date and its deadline's date (Moroccan local date): the time a business has to prepare a bid. A tender without a deadline has none. The median of an even number of windows is the mean of the middle two, so it can end in .5.

**Short response window**:
A response window shorter than half the median response window for tenders in the same category.

**Public buyer**:
The specific administrative unit that publishes a tender (e.g. a provincial office). Belongs to one organisation.
_Avoid_: buyer (on its own), acheteur

**Organisation**:
The parent body (ministry, agency, local authority) that one or more public buyers belong to. On the source platform it is identified by an opaque code.

**Closing soon**:
An open tender whose deadline falls within the next 14 days, grouped as less than 3 days, 3–7 days or 7–14 days left.

**Period**:
The span of publication dates an Insights figure is computed over: the last 7, 30 or 90 days, or all time. The last N days are the N calendar days ending today (Moroccan local date), so a tender published exactly N days ago is outside them. A tender without a publication date is in no period.

**Coverage**:
What the Insights figures are based on: how many tenders fall in the period, the earliest and latest publication dates among them, and how many of the period's tenders have no deadline.

**New this week**:
A tender published in the last 7 days (the 7-day period).

**Top public buyers / categories / locations**:
Tender counts per value over the period, most first. Values that differ only in case or spacing are counted together and shown under their most frequent spelling. A tender's location is the first one shown on the platform, so a multi-location tender counts once.

**DCE archive**:
The single zip file containing a tender's consultation documents, fetched via `TenderDownloader`. One archive per tender (1:1) — there is currently no concept of tracking the individual files inside it separately.
_Avoid_: document (ambiguous between "the archive" and "a file inside it" — always say "DCE archive" for the former)

A tender **has a DCE archive** once it has reached `UPLOADED`: its status is `UPLOADED` or later, or its status is `FAILED` with a last status of `UPLOADED` or later. Tenders that are `DISCOVERED`, `DOWNLOADING`, or failed before upload have none. The rule lives in `persistence.models.has_dce_archive`.

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
