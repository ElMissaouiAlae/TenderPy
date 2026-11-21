# 02: Review and prune the goldens

**What to build:** The operator reviews every generated golden before any mapping or scoring happens, so that wrong goldens never get mapped to chunks or distort the baseline. A golden is removed if its query is ambiguous, its expected output is wrong or not supported by its source passage, its tender tag is wrong, or it duplicates another golden. Every removal is recorded with its reason.

**Blocked by:** 01 (Generate the golden dataset).

**Status:** ready-for-human

- [ ] Every golden has been read against its source passage.
- [ ] Removed goldens are listed in the round log with a reason each.
- [ ] The remaining dataset is about 30–40 goldens, still spread across all chosen tenders.
- [ ] The reviewed dataset is committed.
