# Spec: Dashboard UI tracer bullet (tender list, tender detail, DCE archive download)

Status: ready-for-agent

## Problem Statement

Everything TenderPy knows about tenders lives in the database and in document storage, and the only way to reach it is the CLI or SQL. The operator cannot browse the tenders that have been collected, look at one tender's details, or get its DCE archive without writing code. Upcoming features (search over chunks, per-tender questions, DCE file views) also have nowhere to live: there is no web application, no HTTP API, and no agreed shape for adding pages. The operator wants a first, deliberately thin UI that runs from the database all the way to the browser, so later features can be added to an existing skeleton rather than built from scratch.

## Solution

A small web dashboard backed by a thin HTTP API, both living in this repository.

- The dashboard has a collapsible sidebar with a single "Tenders" entry, and a main area.
- The Tenders page lists every tender that has a DCE archive in storage.
- Clicking a tender opens its own detail page (its own URL), showing the tender's fields and a button to download its DCE archive.
- Status is not shown anywhere in the UI.

A tender **has a DCE archive** when it has reached `UPLOADED`: its status is `UPLOADED` or later, or its status is `FAILED` and its last status is `UPLOADED` or later. Tenders that were discovered but never uploaded, or that failed before upload, are not listed and cannot be opened.

## User Stories

1. As an operator, I want to open the dashboard in my browser, so that I can see collected tenders without using the CLI or SQL.
2. As an operator, I want a sidebar with a "Tenders" entry, so that I always know how to get back to the tender list.
3. As an operator, I want to collapse and expand the sidebar with a toggle, so that I can give the main area more room.
4. As an operator, I want the sidebar to keep working the same way as pages are added later, so that new features have an obvious place to appear.
5. As an operator, I want the Tenders page to list every tender that has a DCE archive, so that everything I can download is in front of me.
6. As an operator, I want tenders without a DCE archive left out of the list, so that I never open a tender I can't download.
7. As an operator, I want tenders that failed during chunking or embedding to still appear, so that a later processing failure does not hide an archive that exists.
8. As an operator, I want each row to show the reference number, so that I can match it to the source platform.
9. As an operator, I want each row to show the tender object (shortened when long), so that I can recognise what the tender is about at a glance.
10. As an operator, I want each row to show the public buyer, so that I know who is procuring.
11. As an operator, I want each row to show the tender end date, so that I can see deadlines.
12. As an operator, I want to click a row to open that tender, so that I can see its details.
13. As an operator, I want each tender's detail page to have its own URL, so that I can bookmark it, reload it, or share it.
14. As an operator, I want the detail page to show the tender ID and organization acronym, so that I can identify the tender the same way the source platform does.
15. As an operator, I want the detail page to show the reference number, object, public buyer, location, category, procurement type, publication date, and end date, so that I have the whole record in one place.
16. As an operator, I want status and last status hidden from the UI, so that the dashboard shows the tender itself rather than our processing state.
17. As an operator, I want a "Download DCE archive" button on the detail page, so that I can get the tender's consultation documents.
18. As an operator, I want the download to save as a zip file with a meaningful filename, so that I can tell archives apart on disk.
19. As an operator, I want opening a detail URL for a tender that does not exist, or has no DCE archive, to show a clear "not found" message, so that a stale link does not leave me on a broken page.
20. As an operator, I want a clear message when the list or detail cannot be loaded (API down, network error), so that I know the problem is not an empty database.
21. As an operator, I want a loading indicator while data is fetched, so that I know the page is working.
22. As an operator, I want an empty-state message when no tender has a DCE archive yet, so that an empty list is not mistaken for an error.
23. As an operator, I want to go back from a detail page to the list, so that I can browse several tenders.
24. As a developer, I want the API to list tenders with a limit and offset, so that the API contract does not change when the UI later gets pagination.
25. As a developer, I want the API to return one tender by its database id, so that the UI's detail route maps directly onto it.
26. As a developer, I want the API to stream the DCE archive through itself, so that downloads work the same with S3 and local storage and no storage credentials or URLs reach the browser.
27. As a developer, I want the "has a DCE archive" rule defined in one place, shared with indexing selection, so that the UI and the indexing pipeline never disagree on which tenders have an archive.
28. As a developer, I want the API built from injected collaborators (a tender lookup and a document storage), so that it can be tested without network or cloud access.
29. As a developer, I want the UI and API runnable locally with one command each, with the UI dev server proxying to the API, so that working on the UI needs no CORS setup.
30. As a developer, I want the UI typed end to end against the API's response shapes, so that contract drift shows up as type errors.

## Implementation Decisions

- **New HTTP API module** (Python, FastAPI) in this repository, alongside the existing packages. It is a thin layer: no business logic beyond mapping records to responses and translating "not found" into HTTP 404.
- **App factory**: the API is built by a factory that takes two collaborators: a read-only tender lookup and a `DocumentStorage`. Production wiring builds them from the existing `Settings`, `Database`, and storage configuration. Tests pass fakes.
- **Read-only tender lookup**: a new read interface over tender records with two operations: list tenders that have a DCE archive (limit, offset) and get one tender by database id (only if it has a DCE archive, otherwise not found). The production implementation lives in the persistence layer next to the existing repository and queries tender records directly.
- **"Has a DCE archive" rule**: status is `UPLOADED` or later, or status is `FAILED` and last status is in the existing `INDEXABLE_LAST_STATUSES` set. Both halves use the existing status enum and set, not a new copy. If a shared helper is introduced, indexing selection should use it too.
- **Tender identity in the API and UI routes** is the database primary key. The domain identity `(tender_id, organization_acronym)` is shown on the detail page and used to find the archive in storage.
- **API contract**:
  - `GET /tenders?limit=&offset=` → a JSON list of tender summaries: id, reference number, tender object, public buyer, tender end date. Sensible default limit, upper bound enforced. Ordering is stable (newest publication first, then id).
  - `GET /tenders/{id}` → tender detail: id, tender ID, organization acronym, reference number, tender object, public buyer, location, category, procurement type, publication date, tender end date. 404 when the tender is missing or has no DCE archive.
  - `GET /tenders/{id}/dce-archive` → the zip bytes, `application/zip`, `Content-Disposition: attachment` with a filename derived from the tender's identity. 404 when the tender is missing, has no DCE archive, or the archive cannot be found in storage.
  - Status and last status are never part of any response.
- **Archive lookup** uses the existing archive naming convention (`dce_archive_name(tender_id, organization_acronym)`) and `DocumentStorage.load_document`, the same path the indexing pipeline uses. Streaming the loaded bytes is fine for v1; true chunked streaming from S3 is a later optimisation.
- **API dependencies** (FastAPI, an ASGI server) are added to the project. Test client dependencies go in the dev group.
- **New UI app** in its own top-level directory of this repository: Vite + React + TypeScript, React Router, plain CSS, no component or styling library.
- **UI structure**: a layout shell (sidebar + main outlet) wraps all routes so future pages are just new routes and sidebar entries. Routes: the tender list (default route redirects to it) and the tender detail page. A small typed API client module holds the response types and fetch functions. Components never call fetch directly.
- **Sidebar**: one nav entry, "Tenders", plus a collapse/expand toggle. The collapsed state is UI-only (remembering it across reloads is optional).
- **Download**: the detail page's button is a plain link to the archive endpoint so the browser handles the download natively.
- **Local dev**: the Vite dev server proxies API paths to the locally running API. The API runs against the application's existing Aiven Postgres and configured document storage through the usual `.env` settings. `compose.yml` is not involved.
- **Domain glossary**: `CONTEXT.md` gains a short note under **DCE archive** defining when a tender has one (reached `UPLOADED`, including `FAILED` with last status `UPLOADED` or later).

## Testing Decisions

- Good tests here exercise external behaviour only: HTTP requests in, status codes, JSON bodies, headers and bytes out. They do not assert on internal calls, ORM queries, or component internals.
- **Primary seam: the HTTP API**, driven through FastAPI's test client against an app built by the factory with an in-memory fake tender lookup and `LocalDocumentStorage` on a temp directory. Cases:
  - list returns only tenders with a DCE archive, with the summary fields and no status fields
  - list honours limit and offset
  - detail returns all detail fields for a tender with a DCE archive
  - detail returns 404 for an unknown id and for a tender without a DCE archive
  - archive download returns the stored zip bytes with `application/zip` and an attachment filename
  - archive download returns 404 for an unknown tender, a tender without a DCE archive, and a tender whose archive is missing from storage
- **Query check against the real database**: one integration test in the existing integration test suite, run against the application's Aiven Postgres like the other integration tests, covering the production tender lookup's "has a DCE archive" filter. It checks that `DISCOVERED`, `DOWNLOADING`, and `FAILED`-before-upload tenders are left out, and that `UPLOADED`, `INDEXED`, and `FAILED` with last status `UPLOADED` (or later) are included. It cleans up the rows it creates.
- **Prior art**:
  - the indexing pipeline tests drive the public entry point with fakes for storage and the repository
  - the file storage tests exercise `LocalDocumentStorage` on a temp directory
  - the integration test for indexing selection checks a status-based selection query against the real database
- **UI**: no automated tests in this slice. It is checked manually by running the API and the UI dev server against the real database and clicking through list → detail → download.

## Out of Scope

- Authentication and authorisation.
- Filtering, sorting controls, and full-text search in the list.
- Pagination controls in the UI (the API already accepts limit and offset).
- Showing status, last status, or any processing or pipeline state.
- DCE file and chunk views, search hits, or question answering in the UI.
- Styling or component libraries, theming, dark mode.
- Presigned S3 URLs or direct-from-S3 downloads.
- Deployment, containerisation, and production hosting of the API or UI.
- UI automated tests.

## Further Notes

- This is a tracer bullet: the goal is a working path from database to browser that later features can be added to, not a finished product. Prefer the simplest thing at each layer.
- Work happens on a new branch `feat/ui-dashboard` cut from `master` after the in-progress retrieval changes have been committed, raised as a PR, and merged by the user.
- Tender dates are stored as strings on the tender record. The API passes them through unchanged in v1.
