# Spec: Dashboard redesigned to the BankDash Figma template

Status: ready-for-agent

Replaces `.scratch/ui-dashboard-design/spec.md` as the dashboard's visual reference.

## Problem Statement

The dashboard currently follows an earlier design canvas (purple accent, system font). The operator has picked a different visual reference: the "BankDash" Figma template. They want the dashboard to look like that template, with its fonts and colours, while still showing only what TenderPy has today. That means the tender list and the tender detail page. Analytics may come later, but nothing for it is built now.

## Solution

Restyle the layout shell, the tender list and the tender detail page in the template's visual language. Use the template's Inter font and its navy/blue palette in place of the purple. Map the template's "Recent Transactions" table onto the tender list, adding Previous/Next paging and a Download button on each row. Everything the template shows that TenderPy can't back (cards, expense charts, search, notifications, avatar, filter tabs, extra sidebar pages) is left out, not faked.

## User Stories

1. As an operator, I want the dashboard to use the template's font, colours, cards and buttons, so that it has one consistent, finished look.
2. As an operator, I want the sidebar to show the TenderPy name and a single "Tenders" entry, marked as active the way the template marks it, so that I know where I am and never click a dead entry.
3. As an operator, I want a top bar showing the current page's title, so that the page reads like the template without controls that do nothing.
4. As an operator, I want the tender list to show object, reference, public buyer and deadline in a template-style table, so that I can scan tenders quickly.
5. As an operator, I want a Download button on each row, so that I can grab a tender's DCE archive without opening it.
6. As an operator, I want clicking anywhere else on a row to open the tender, so that I don't have to aim at a small link.
7. As an operator, I want Previous and Next controls, so that I can move through more tenders than fit on one page.
8. As an operator, I want the page number kept in the URL, so that refreshing, sharing a link or going back keeps my place.
9. As an operator, I want the detail page restyled to match, with the download as its main action and the remaining fields in a "Key facts" card, so that the whole dashboard looks the same.
10. As an operator, I want the dashboard to work on my phone, with the sidebar behind a menu button, so that I can check tenders away from my desk.
11. As an operator, I want text readable and every control reachable by keyboard, so that the dashboard stays easy to use.
12. As a developer, I want the template's values defined once as CSS custom properties, so that future pages (such as analytics) reuse them.

## Implementation Decisions

- **Design source**: Figma file `uiafXy2Gqbsu1uK6Vxj9QV` ("BankDash" template). Frames:
  - `78:351` "Main Dashboard": layout shell (sidebar, top bar, page background).
  - `105:0` "Transaction": the tender list. Its "Recent Transactions" table, its outlined "Download" buttons and its Previous/Next pager are the source.
  - `169:3352` "Dashboard for Mobile" and `181:279` "Transaction for Mobile": phone layout.

  Read these frames with `get_screenshot` or `get_design_context` on those node ids. Don't call `get_metadata` on the whole page; it returns over 500K characters. The template is a visual reference only. Its brand (the "BankDash" name and logo), its content and its banking features are not copied.
- **Colours and type**: these replace the purple tokens.
  - From the file's variables:
    - Inter for all text; headings Semi Bold 28/22 px, section headings Medium 18 px, body 16/15 px, small 13 px.
    - "Primary 2" `#343C6A` for titles and navy text.
    - "Primary 3" `#2D60FF`.
    - Card shadow "Shadow 1": `#E7E4E8CC`, offset 4/4, blur 18, spread −2.
  - Read off the frames (confirm with `get_design_context` when implementing):
    - Bright blue accent `#1814F3` for the pager, the outlined buttons and the filled buttons. (Confirmed against `78:351` on 2026-11-21: the active nav bar and active nav text are "Primary 3" `#2D60FF`, not `#1814F3`.) (Confirmed against `105:0` on 2026-11-21: the outlined Download buttons are navy `#123288` at rest; one row shows `#1814F3`, used as their hover colour.)
    - Body text `#232323`.
    - Page background `#F5F7FA`, white cards, light borders `#E6EFF5`.
  - The template's muted grey-blue `#718EBF` is darkened to about `#5B6F96` so muted text reaches 4.5:1 contrast on white. Inactive nav text (`#B1B1B1` in the template, 2.1:1) uses the same `#5B6F96`. Error text keeps `#B42318`, since the template's reds fail 4.5:1 as text. Every other value matches the template.
  - All of these are CSS custom properties on the root. Components use the properties, never raw values. No dark mode.
- **Font loading**: Inter is bundled with the app from the `@fontsource-variable/inter` npm package, falling back to the system sans stack. No request goes to Google Fonts or any other CDN. This is the only new dependency; there's still no styling or component library.
- **Layout shell**:
  - The sidebar shows the TenderPy name and only "Tenders", with the template's blue bar and blue text on the active entry and inline stroke SVG icons. The single nav-entry list stays the one place a page is registered.
  - The current collapse toggle is removed, since the template has none.
  - The top bar shows only the current page's title (28 px, Primary 2). No search, settings, notifications or avatar.
  - At phone width, the sidebar becomes a drawer opened by a menu button in the top bar, following the mobile frames. The button has `aria-label` and `aria-expanded`, and the drawer closes on navigation and on Escape.
- **Tender list**:
  - A white rounded card containing a table in the "Recent Transactions" style. Columns:
    - **Object**: shortened when long, with the full text in a hover title. "Untitled tender" when missing.
    - **Reference**
    - **Public buyer**
    - **Deadline**: the tender end date passed through unchanged.
    - A **Download** column: an outlined pill button linking to `dceArchiveUrl(id)`.
  - The template's round per-row icon is left out. Missing values show a muted "—".
  - Clicking anywhere on the row except Download opens `/tenders/:id`. The row stays a real link. Download is a separate plain link that the row link doesn't cover, so it downloads without navigating. Tab reaches the row link and the Download link separately.
  - Paging:
    - 20 tenders per page. Previous/Next only, in the template's pager style. No page numbers, because the API returns no total count.
    - The page lives in the URL as `?page=N`, 1-based. A missing, non-numeric or less-than-1 value means page 1.
    - The request uses `limit=20, offset=(N−1)×20`.
    - Previous is disabled on page 1. Next is disabled when a page returns fewer than 20 tenders.
    - An empty page beyond page 1 says "No more tenders." and keeps Previous enabled. When the total is an exact multiple of 20, that's what you land on after the last full page; this is accepted.
  - Loading, empty ("No tender has a DCE archive yet.") and error messages keep their wording and are restyled.
  - Not built:
    - "My Cards" and "My Expense" panels.
    - The All/Income/Expense tabs.
    - Page numbers.
    - Search.
- **Tender detail page**:
  - The structure stays the same and is restyled:
    - "← Back to tenders" link.
    - Category and procurement-type tags.
    - The object as the title.
    - A muted line: "public buyer · Ref. reference number · Published publication date".
    - A filled blue "Download DCE archive" button, kept as the plain link to `dceArchiveUrl(id)` it already is.
    - A white "Key facts" card with muted labels holding tender ID, organization acronym, location and tender end date. (Confirmed against `78:351` on 2026-11-21: the template titles its cards from above, as with "My Cards", in Semi Bold 22 px Primary 2. So "Key facts" sits above its card at that size, 18 px at phone width. The filled button follows the "Send" pill: 50 px high, `#1814F3`, white Medium 16 px. Cards have no border, only "Shadow 1", which the tender list's card now shares.)
  - Every field the detail contract returns appears exactly once. A null value shows a muted "—". An empty tag is left out.
  - Loading, not-found and error states are restyled.
- **Backend**: unchanged. The DCE archive endpoint (`GET /tenders/{id}/dce-archive`), `GET /tenders` with `limit`/`offset`, `GET /tenders/{id}` and the typed client stay exactly as they are.
- **Accessibility**: real links and buttons only, text at 4.5:1 contrast, touch targets at least 44 px, visible focus styles, and `aria-hidden` on decorative SVGs.
- **Glossary**: no domain terms change. `CONTEXT.md` is untouched.

## Testing Decisions

- No UI automated tests, as in the earlier specs. The automated seam stays the HTTP API through FastAPI's test client. The API isn't changed, so the existing API tests must pass unchanged.
- The UI TypeScript build (`npm run build` in `ui/`) must pass.
- Manual check with the API and UI dev server running against a reachable database, side by side with frames `78:351`, `105:0` and `181:279`:
  - the font is Inter and the palette matches the template;
  - the sidebar shows only "Tenders", marked active;
  - row click opens the detail page, and the row Download button saves a zip without navigating;
  - Previous/Next and `?page=N` behave as specified, including invalid values;
  - the detail page shows every field once;
  - loading, empty, error and not-found states are styled;
  - the phone-width drawer works;
  - keyboard Tab order reaches the row link, then Download.

## Out of Scope

- Analytics, Overview or any page other than Tenders.
- Search, settings, notifications, avatar, filter tabs, page numbers, sorting.
- Any API, database or persistence change, including a total count for paging.
- The template's brand, logo and banking content.
- Dark mode and theming.
- Glossary changes.

## Further Notes

- Work continues on `feat/ui-dashboard`.
- Manual checks need the database reachable. The Aiven service was unreachable (DNS failure) as of 2026-11-20.
