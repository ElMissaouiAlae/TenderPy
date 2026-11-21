# 03: DCE archive download

**What to build:** On a tender's detail page, the operator clicks "Download DCE archive" and the browser saves the tender's zip with a filename derived from the tender's identity. The API streams the archive through itself from the configured document storage (S3 or local), so no storage URLs or credentials reach the browser. See `.scratch/ui-dashboard/spec.md`.

**Blocked by:** 02 (Tender detail page), `ui-dashboard-design/01` (Design tokens and layout shell)

**Status:** ready-for-agent

- [ ] `GET /tenders/{id}/dce-archive` loads the archive via the existing archive naming convention and `DocumentStorage`, responding `application/zip` with `Content-Disposition: attachment` and a meaningful filename
- [ ] 404 when the tender is unknown, has no DCE archive, or the archive is missing from storage
- [ ] Detail page has a "Download DCE archive" button implemented as a plain link to the endpoint, styled as the design's primary accent button and the page's only action, per `.scratch/ui-dashboard-design/spec.md`
- [ ] pytest via the test client with `LocalDocumentStorage` on a temp directory: correct bytes and headers, plus all three 404 cases
- [ ] Manually verified: downloading a real tender's DCE archive from the detail page yields a valid zip
