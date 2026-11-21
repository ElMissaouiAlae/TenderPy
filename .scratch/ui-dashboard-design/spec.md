# Spec: Dashboard design applied to the tender list and tender detail

Status: ready-for-agent

## Problem Statement

The dashboard tracer bullet (`.scratch/ui-dashboard/spec.md`) gives the operator a working path from the database to the browser, but its pages are bare: an unstyled sidebar with a text toggle, and a plain four-column table. A design for the dashboard's future now exists as a design canvas (https://claude.ai/artifact/1WrXRR8ZyfXNqpw4rD6PMj, artboards "Overview — recommendations" and "Tender detail"). That canvas is a vision of a much larger product than what exists today. It shows match scores, a company profile, saved tenders, alerts, AI questions, and tender facts the system does not store. The operator wants the pages that exist today to look like that design, without pulling in any of the product the design imagines and without changing how the database and the API work.

## Solution

Restyle the dashboard's layout shell and tender list, and build the tender detail page, in the design's visual language, showing only what TenderPy actually has today.

- The sidebar, colours, cards, table and buttons follow the design canvas.
- The sidebar lists only pages that exist: today, just "Tenders".
- The tender list is a "Best matches"-style table with two columns: the tender (its object, with public buyer and reference number beneath) and the deadline (the tender end date as stored).
- The tender detail page has a design-style header, a single "Download DCE archive" action, and a "Key facts" card.
- Where the design and the tender record disagree, the tender record wins: design-only fields and features are left out, not faked.

## User Stories

1. As an operator, I want the dashboard to have a consistent, finished look, so that it feels like a tool I can rely on rather than a prototype.
2. As an operator, I want the sidebar to show the product name at the top, so that I know which application I am in.
3. As an operator, I want the sidebar entries styled as in the design, with the current page highlighted, so that I can always see where I am.
4. As an operator, I want the sidebar to list only pages that exist, so that I never click an entry that leads nowhere.
5. As an operator, I want to collapse and expand the sidebar with a clearly drawn toggle, so that I can give the main area more room.
6. As an operator, I want the collapsed sidebar to still show something recognisable for each entry, so that I can navigate without expanding it.
7. As an operator, I want the tender list page to have a heading and a short line explaining what it lists, so that I understand that only tenders with a DCE archive appear.
8. As an operator, I want the tender list shown inside a card, as in the design, so that the list reads as one block.
9. As an operator, I want each row's main cell to show the tender object prominently, so that I can recognise what the tender is about at a glance.
10. As an operator, I want a long tender object shortened, with the full text still reachable on hover, so that rows stay compact without losing information.
11. As an operator, I want the public buyer and reference number shown beneath the object in a quieter style, so that I can tell who is procuring and match it to the source platform without extra columns.
12. As an operator, I want a deadline column showing the tender end date exactly as recorded, so that I can see deadlines without the UI guessing at the date format.
13. As an operator, I want rows to react on hover, so that I can tell they are clickable.
14. As an operator, I want to click anywhere on a row to open that tender, so that I don't have to aim at a small link.
15. As an operator, I want the list's loading, empty and error messages styled to match the design, so that they read as part of the page rather than as stray text.
16. As an operator, I want the detail page to have a "Back to tenders" link at the top, so that I can return to the list.
17. As an operator, I want the tender's category and procurement type shown as small tags above the title, so that I can classify the tender at a glance.
18. As an operator, I want the tender object as the detail page's title, so that the most meaningful text is the most visible.
19. As an operator, I want a line under the title with the public buyer, the reference number, and the publication date, so that the tender's identity on the source platform is right under its name.
20. As an operator, I want the "Download DCE archive" button to be the page's primary action, styled with the design's accent, so that the one thing I can do on the page is obvious.
21. As an operator, I want a "Key facts" card showing the tender ID, organization acronym, location and end date, so that the rest of the record is in one tidy place.
22. As an operator, I want an empty field shown as an explicit placeholder rather than a blank gap, so that I can tell missing data from broken layout.
23. As an operator, I want the detail page's loading, not-found and error states styled to match the design, so that a stale link still lands on a page that looks intentional.
24. As an operator, I want no status, last status, or processing state shown anywhere, so that the dashboard keeps showing the tender itself.
25. As an operator, I want no match scores, budgets, saved-tender buttons, alerts or AI questions shown yet, so that nothing on screen implies data or features that don't exist.
26. As an operator, I want the pages to stay usable at phone width, so that I can check a tender from my phone.
27. As an operator, I want text and controls to have enough contrast and size, so that the dashboard is easy to read and use.
28. As an operator, I want buttons and links to be reachable with the keyboard, so that I can use the dashboard without a mouse.
29. As a developer, I want the design's colours, radii and spacing defined once as CSS custom properties, so that later pages reuse them instead of copying values.
30. As a developer, I want the visual reference for the dashboard recorded in the spec, so that the next page I add follows the same design.
31. As a developer, I want the API and its contract untouched by this work, so that the restyle cannot break the backend or its tests.

## Implementation Decisions

- **Visual reference**: the design canvas at https://claude.ai/artifact/1WrXRR8ZyfXNqpw4rD6PMj. It is a future vision, not a specification: only its visual language and the layout of the parts that map onto today's tender record are adopted. Where the canvas and the tender record disagree, the tender record wins.
- **Design source**: Figma file `uiafXy2Gqbsu1uK6Vxj9QV` ("BankDash" template). Node `105:0` "Transaction" is the source for the tender list; node `78:351` "Main Dashboard" is the source for the layout shell (sidebar and main area). Read these frames with `get_screenshot` or `get_design_context` on those node ids, rather than `get_metadata` on the whole page (which returns over 500K characters).
- **No backend change**: the database, the "has a DCE archive" rule, the API contract (`GET /tenders`, `GET /tenders/{id}`, `GET /tenders/{id}/dce-archive`) and the typed API client's response types stay exactly as the tracer-bullet spec defines them. This spec only changes UI components, pages and styles.
- **Styling**: plain CSS as before, no component or styling library. The design's look becomes a small set of CSS custom properties defined once on the root: the accent `#6A4BE0` with its darker hover shade, the slate page background (`#F8FAFC`), white card surfaces, border and muted-text greys, text colour, and the corner radii used for cards, buttons and pills. Components use the properties, not raw values. No dark mode.
- **Fonts**: the design's system sans stack. No web font is added.
- **Icons**: inline stroke SVG, as in the design, with `aria-hidden` on decorative ones. No icon library and no emoji. The sidebar toggle stops using `«`/`»` characters.
- **Layout shell**: the existing shell (sidebar plus main outlet, with collapse state held in the UI only) keeps its structure and its single nav-entry list, which stays the one place a new page is registered. It is restyled to the design: product name at the top, design-style nav entries with an active state, and a drawn toggle. Nav entries exist only for routes that exist. The design's other sidebar items (Overview, Recommendations, Saved, Alerts, Company profile), the promo card and the avatar are not built.
- **Tender list page**:
  - Page heading "Tenders" with a one-line description saying the list holds every tender whose DCE archive is available.
  - The list sits in a card, as a table styled like the design's "Best matches" table.
  - Two columns: **Tender** and **Deadline**.
    - Tender: the tender object (shortened when long, with the full text in a hover title), with "public buyer · reference number" beneath it in muted text.
    - Deadline: the tender end date passed through unchanged, as the API returns it.
  - The whole row navigates to the tender's detail route. It stays a real link, so it works with the keyboard and with open-in-new-tab.
  - Loading, empty and error messages keep their current wording and are restyled.
  - Not built: the category column, budget, match score, "days left" countdown, the category filter tabs, KPI tiles, "Closing soon" and "What we match on" panels, and the "Showing N of M" footer.
- **Tender detail page** (the page that issue 02 of the tracer bullet builds):
  - A "Back to tenders" link above the header.
  - Header: category and procurement type as pills, the tender object as the page title, then "public buyer · Ref. reference number · Published publication date" in muted text.
  - Actions: the "Download DCE archive" button only, styled as the design's primary button and still a plain link to the archive endpoint, as the tracer-bullet spec requires.
  - A "Key facts" card in the design's label/value style, holding tender ID, organization acronym, location and tender end date.
  - Every field the detail contract returns appears exactly once on the page. A null field shows a muted placeholder, and an empty pill is omitted.
  - Loading, not-found and error states are restyled to match.
  - Not built: the Save button, the "N days left" chip, the match score and "Why this is a strong match" panel, budget and other key facts the tender record does not hold, the DCE files list, "Ask about this tender", and the timeline.
- **Responsive behaviour**: pages are fluid inside a max-width container. At phone width the sidebar collapses or stacks, the header and actions wrap, and the table scrolls inside its card rather than the page.
- **Accessibility**: real links and buttons only. The icon-only toggle keeps its `aria-label` and `aria-expanded`. Text meets 4.5:1 contrast, including muted labels. Touch targets are at least 44 px.
- **Glossary**: no terms from the design (recommendation, match, company profile and the like) are added to the domain glossary. They will be discussed later. The glossary is unchanged by this spec.
- **Relationship to the tracer bullet**: the tender list (issue 01) is already built, so restyling it and the layout shell is new work. The tender detail page (issue 02) and the download button (issue 03) are not built yet. They should be built straight to this design rather than built plain and restyled afterwards.

## Testing Decisions

- A good test here checks what the operator sees and can do, not how components are put together. No test asserts on CSS, class names or component internals.
- **No new test seam.** The only automated seam stays the HTTP API through FastAPI's test client, as the tracer-bullet spec set up. This spec does not change the API, so the existing API tests must keep passing unchanged. That shows the restyle didn't touch the backend.
- **UI**: no automated tests, consistent with the tracer-bullet spec. Checked manually by running the API and the UI dev server against the application's database and checking that:
  - the sidebar shows only "Tenders", highlights it, and collapses and expands
  - the list shows the two columns with real tenders, shortens long objects, and opens the detail page on row click
  - the detail page shows every detail field once, with placeholders for nulls, and the download button saves a valid zip
  - loading, empty, not-found and error states render in the new style (stop the API to see the error state; open an unknown id to see not-found)
  - pages hold up at phone width
  - the canvas and the running pages look alike side by side
- The UI's TypeScript build must pass, so the components stay typed against the unchanged API client.
- **Prior art**: the tracer-bullet spec's manual click-through (list → detail → download), and its API tests driven through the test client.

## Out of Scope

- Any change to the database, persistence layer, API endpoints, API contract or the "has a DCE archive" rule.
- New pages: Overview, Recommendations, Saved, Alerts, Company profile.
- Match scores, recommendations, company profiles and multi-tenancy, which the design assumes and which will be discussed separately.
- Fields the tender record does not hold: budget, caution provisoire, qualification, execution period, site visit, timeline dates.
- Per-tender AI questions ("Ask about this tender"). This is a planned feature to be built later, on retrieval over that tender's chunks with citations.
- The DCE files list on the detail page.
- Deadline countdowns or any date parsing. Tender dates stay pass-through strings.
- Filtering, sorting, category tabs, search and pagination controls.
- Saving tenders, alerts, notifications.
- Dark mode, theming, web fonts, styling or component libraries.
- UI automated tests.
- Glossary changes.
- Updating the design canvas to match what is built.

## Further Notes

- The canvas will keep changing as a prototype. Anything this spec leaves out should come from the canvas only once the tender record and API can back it.
- Multi-tenancy is in the design's future, not today's. Nothing built here should assume a single company in a way that's hard to undo later, but nothing should prepare for tenants either.
- Work continues on `feat/ui-dashboard`. The tracer-bullet issues 02 and 03 should be read together with this spec when they are picked up.
- `ui/src/components/Layout.tsx` has an uncommitted change that only adds trailing whitespace. The layout-shell restyle rewrites that file, so the change can be discarded.
