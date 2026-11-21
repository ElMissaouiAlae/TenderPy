# 01: Tender list, end to end

**What to build:** Running the API and the UI dev server against the application's Aiven database, the operator opens the dashboard, sees a layout with a collapsible sidebar holding a single "Tenders" entry, and the Tenders page lists every tender that has a DCE archive (reference number, tender object shortened when long, public buyer, tender end date). Tenders without a DCE archive are not listed; tenders that failed after upload are. No status is shown. This ticket also lays down the skeleton later features attach to: the API app factory with injected collaborators, the read-only tender lookup, the UI layout shell and typed API client, and the dev proxy. See `.scratch/ui-dashboard/spec.md`.

**Blocked by:** None (can start immediately)

**Status:** done

- [x] "Has a DCE archive" rule defined once in persistence, built from the existing `INDEXABLE_LAST_STATUSES` (status `UPLOADED` or later, or `FAILED` with last status `UPLOADED` or later); indexing selection does not end up with a divergent copy
- [x] Read-only tender lookup lists tenders with a DCE archive, with limit and offset and stable ordering (newest publication first, then id)
- [x] API built by a factory taking a tender lookup and a `DocumentStorage`; production wiring uses existing `Settings`/`.env`
- [x] `GET /tenders?limit=&offset=` returns summaries (id, reference number, tender object, public buyer, tender end date), never status or last status; default limit and an enforced upper bound
- [x] FastAPI and an ASGI server added as dependencies; test client in the dev group
- [x] UI app (Vite + React + TypeScript, React Router, plain CSS) with a layout shell: sidebar with collapse/expand toggle and a "Tenders" nav entry, main outlet; default route goes to the tender list
- [x] Typed API client module; components never call fetch directly
- [x] List page shows loading, empty-state, and error messages
- [x] Vite dev server proxies API paths to the local API (no CORS setup needed)
- [x] pytest via the test client with a fake tender lookup: only tenders with a DCE archive, summary fields only, limit/offset honoured
- [x] Integration test against the Aiven database (alongside the existing indexing-selection one): `DISCOVERED`, `DOWNLOADING` and `FAILED`-before-upload excluded; `UPLOADED`, `INDEXED` and `FAILED` with last status `UPLOADED`+ included; created rows cleaned up
- [x] `CONTEXT.md` gains a note under **DCE archive** on when a tender has one
- [x] Manually verified: both servers running, real tenders visible, sidebar toggles
