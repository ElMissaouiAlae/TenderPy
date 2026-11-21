# 03: DCE archive download

**What to build:** On a tender's detail page, the operator clicks "Download DCE archive" and the browser saves the tender's zip with a filename derived from the tender's identity. The API streams the archive through itself from the configured document storage (S3 or local), so no storage URLs or credentials reach the browser. See `.scratch/ui-dashboard/spec.md`.

**Blocked by:** 02 (Tender detail page), `ui-dashboard-design/01` (Design tokens and layout shell)

**Status:** ready-for-human

- [x] `GET /tenders/{id}/dce-archive` loads the archive via the existing archive naming convention and `DocumentStorage`, responding `application/zip` with `Content-Disposition: attachment` and a meaningful filename
- [x] 404 when the tender is unknown, has no DCE archive, or the archive is missing from storage
- [x] Detail page has a "Download DCE archive" button implemented as a plain link to the endpoint, styled as the design's primary accent button and the page's only action, per `.scratch/ui-dashboard-design/spec.md`
- [x] pytest via the test client with `LocalDocumentStorage` on a temp directory: correct bytes and headers, plus all three 404 cases
- [ ] Manually verified: downloading a real tender's DCE archive from the detail page yields a valid zip

## Comments

### 2026-11-21: implemented, manual check outstanding

`GET /tenders/{id}/dce-archive` streams the archive through the API (`application/zip`, `Content-Disposition: attachment; filename="<tender_id>_<organization_acronym>.zip"`). Both storage adapters now raise `DocumentNotFoundError` for a missing archive (a missing local file, or S3 `NoSuchKey`), and the API turns it into a 404. The detail page has a "Download DCE archive" link styled as the primary accent button.

Tested through the test client (bytes and headers; 404 for unknown/no-archive and for missing from storage) and at the storage adapters (missing local file, S3 `NoSuchKey` via botocore `Stubber`). The fake lookup returns no tender for both "unknown" and "no DCE archive", so one test covers both; the real filter is covered by `integration_tests/tender_lookup.py`. All 3,808 stored tender identities are plain ASCII with no quotes, so the raw `filename="…"` header is safe.

**Open:** the manual download against real S3 failed with `RequestTimeTooSkewed`. This machine's clock was one hour behind AWS (10:09 UTC locally vs 11:09 at S3). Fix the clock (System Settings → General → Date & Time, set automatically), then run `python -m api` and the UI dev server, open a tender, click "Download DCE archive" and check that the zip opens. Unknown ids already return 404 against the real database.
