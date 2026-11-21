# 05: Doc pointers: ticket shipping and Figma source

**What to build:** Two doc pointers, each fixing a gap the retro found.
- The issue-tracker doc gains a "When a ticket ships" section: in the same commit as the code, tick every acceptance box, set `Status: done`, and stage the ticket file (and its feature folder, if untracked). Then an agent finishing a ticket leaves the tracker matching the code.
- The dashboard-design spec gains a "Design source" line: Figma file `uiafXy2Gqbsu1uK6Vxj9QV` ("BankDash" template), node `105:0` "Transaction" (tender list), node `78:351` "Main Dashboard" (layout shell). It says to use `get_screenshot` / `get_design_context` on those node ids instead of calling `get_metadata` on the whole page.

Spec: `.scratch/agent-environment/spec.md`.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] The issue-tracker doc has a "When a ticket ships" section with the three actions, written as positive steps
- [ ] No CLAUDE.md line is added; the issue-tracker doc stays the single source for ticket conventions
- [ ] The dashboard-design spec has a "Design source" line with the file key, both node ids, and each frame's role in TenderPy
- [ ] The Design source line names the Figma calls to make on those nodes
