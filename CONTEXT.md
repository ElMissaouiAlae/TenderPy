# Tender Crawler

Discovers public tenders, downloads their DCE (Dossier de Consultation des Entreprises) archive, uploads that archive to durable storage, and records the result against a `TenderRecord`.

## Language

**Tender**:
A single procurement opportunity discovered from the source platform, identified by `(tender_id, organization_acronym)`.

**DCE archive**:
The single zip file containing a tender's consultation documents, fetched via `TenderDownloader`. One archive per tender (1:1) — there is currently no concept of tracking the individual files inside it separately.
_Avoid_: document (ambiguous between "the archive" and "a file inside it" — always say "DCE archive" for the former)

**Status**:
The current step a tender's processing has reached, stored on `TenderRecord.status` (`TenderStatus` enum): `DISCOVERED → DOWNLOADING → UPLOADED → INDEXED`, or `FAILED` if any step errors.

- `DISCOVERED`: the tender row exists — written immediately when the tender is found, before download starts.
- `DOWNLOADING` / `UPLOADED`: fetching the DCE archive and saving it to document storage (S3), in one step.
- `INDEXED`: the terminal, fully-processed state — the final save/commit, always after download and upload.
- `FAILED`: a step errored; see **Last status** below for how resume works.

**Last status**:
`TenderRecord.last_status` — nullable field that, only while `status = FAILED`, holds the last status the tender *successfully* completed (e.g. `UPLOADED` means "resume from indexing"). Cleared back to null the moment a retry starts moving the tender forward again. Has no meaning when `status != FAILED`.
