# Spec: Agent environment fixes from the 2026-11-21 retro

Status: ready-for-agent

## Problem Statement

Coding agents working in TenderPy keep losing time, and sometimes giving the operator wrong answers, because the repo doesn't tell them what they need to know:

- **Broken code goes unnoticed until runtime.** There is no pre-commit hook, no CI, and no ruff configuration. `ruff check` currently reports 61 errors. An indentation error in the HTTP client only showed up when the operator asked to run the project and the API crashed on import.
- **Ticket status falls behind the code.** Ten tickets that had shipped were still marked `ready-for-agent`, and five feature folders under `.scratch/` had never been committed. A grilling session told the operator that the DCE archive download already existed, then had to take it back. The operator then had to spend a whole session reconciling ticket statuses.
- **A database outage looks like the backend being down.** The API starts and serves `/docs` even when the database can't be reached. On the Aiven free plan, the database powers off when idle and its hostname stops resolving. `/tenders` then returns 500, and the operator reasonably concluded "the backend isn't running".
- **There's no recipe for running the project.** Each "run the project" request makes the agent work out from scratch, by reading several config files, how to start the API and the UI, and where the database comes from.
- **The design source isn't recorded.** The dashboard redesign is based on two frames of a large Figma file. The spec doesn't say which file or which frames, so an agent asked for the page structure got back over 500K characters and had to search through it.

## Solution

- **A lint and test guardrail runs before every commit.** Ruff is configured and the codebase passes it. A pre-commit hook runs ruff, the Python tests, and the UI typecheck, and blocks the commit if any of them fail.
- **The issue-tracker conventions say what to do when a ticket ships.** In the same commit as the code: tick every acceptance box, set `Status: done`, and stage the ticket file (and its feature folder, if it isn't tracked yet).
- **The API has a health endpoint that reports whether the database is reachable.** `GET /health` returns 200 when the database answers, and 503 with a short reason when it doesn't. The API also logs one clear line at startup if the database can't be reached. It still starts either way, so `/docs` and `/health` remain available.
- **A project run skill gives the start commands** for the API and the UI dev server. It points to `/health` as the first thing to check, and records the gotcha that the Aiven free plan powers off when idle.
- **The dashboard design spec names its Figma source.** It records the file key and the node ids of the frames it uses, and says to read those nodes directly instead of fetching the whole page's structure.

## User Stories

1. As the operator, I want a commit to be rejected when the Python code has a syntax error, so that a broken module never reaches the branch.
2. As the operator, I want a commit to be rejected when ruff reports an error, so that lint debt stops building up.
3. As the operator, I want a commit to be rejected when the Python tests fail, so that regressions are caught before they're recorded.
4. As the operator, I want a commit to be rejected when the UI typecheck fails, so that type errors in the dashboard are caught as early as Python errors.
5. As the operator, I want the guardrail to run with one command I can also run by hand, so that I can check my work before committing.
6. As the operator, I want the guardrail to finish quickly, so that I don't start skipping it.
7. As the operator, I want the guardrail to leave out the integration tests that need the live database and S3, so that commits work offline and while Aiven is powered off.
8. As the operator, I want the existing ruff errors fixed in one dedicated change, so that turning on the guardrail doesn't block unrelated work.
9. As the operator, I want ruff's rule set written down in the project config, so that the agent and I lint against the same rules.
10. As a coding agent, I want ruff's output to name the file and line, so that I can fix a failure without searching.
11. As a coding agent finishing a ticket, I want the issue-tracker conventions to tell me to set `Status: done` and tick the boxes in the same commit, so that the ticket and the code never disagree.
12. As a coding agent finishing a ticket, I want to be told to stage the ticket file and an untracked feature folder, so that specs and tickets don't stay uncommitted.
13. As a coding agent planning work, I want ticket statuses I can trust, so that I don't tell the operator that something exists when it doesn't.
14. As the operator, I want the done-marking rule to fit the existing `Status:` line convention, so that ticket state is still read in one place.
15. As the operator, I want `GET /health` to return 200 when the database answers, so that I can confirm the whole stack is up with one request.
16. As the operator, I want `GET /health` to return 503 with a short reason when the database can't be reached, so that I can tell "backend down" apart from "database down".
17. As the operator, I want the health response to leave out the database URL and credentials, so that it's safe to show in a browser.
18. As the operator, I want the API to log one clear line at startup when the database can't be reached, so that the terminal shows the cause without me sending a request.
19. As the operator, I want the API to keep starting when the database is down, so that `/docs` and `/health` stay available while I investigate.
20. As a coding agent asked "why isn't the backend running", I want to check `/health` first, so that I diagnose in one call instead of reading tracebacks.
21. As the operator, I want the health check to finish within a few seconds when the database host doesn't resolve, so that the endpoint doesn't hang.
22. As the dashboard UI, I want `/health` to be a plain JSON endpoint, so that a status indicator could be added later without changing the API.
23. As a coding agent asked to run the project, I want a run skill that gives the API and UI start commands, so that I don't have to rebuild them from several config files.
24. As a coding agent running the project, I want the skill to tell me the database comes from `DB_URL` in `.env`, so that I don't go looking for a local Postgres or a compose file.
25. As a coding agent running the project, I want the skill to warn that the Aiven free plan powers off when idle, so that I recognise the failure and tell the operator to power it on.
26. As a coding agent running the project, I want the skill to start both processes in the background and tell me where their logs go, so that I can read the errors afterwards.
27. As a coding agent working on the dashboard design, I want the spec to give the Figma file key and the frame node ids for the tender list and the dashboard layout, so that I can read exactly those frames.
28. As a coding agent working on the dashboard design, I want the spec to say which Figma calls to make on those nodes, so that I don't fetch the whole page's structure.
29. As the operator, I want the Figma pointer to name each frame by its role in TenderPy, so that later readers know why that frame matters.

## Implementation Decisions

- **Ruff configuration** goes in the project's existing Python packaging config. It targets the project's Python version, includes the default rule set plus import sorting, and excludes the virtualenv, `node_modules`, `.scratch`, and the vector store. Existing errors are fixed in a separate preparatory commit before the hook is turned on.
- **Guardrail runner:** a shell script checked into the repo runs, in order and stopping at the first failure: `ruff check`, `ruff format --check` only if the codebase is already formatted (otherwise left out for now), `pytest` on the unit test directory only, and the UI `typecheck` script. Git's pre-commit hook calls this script. The repo doesn't adopt the `pre-commit` framework, which avoids a new dependency for a single-developer repo. A one-line install step (pointing `core.hooksPath` at a tracked hooks directory) makes the hook live in every clone.
- **The integration tests stay out of the guardrail.** They need the live Aiven database and S3, so they're run by hand, as they are today.
- **Issue-tracker conventions:** the issue-tracker doc under `docs/agents/` gains a "When a ticket ships" section with the three actions listed in the Solution. This doc is the single source for ticket conventions, and the `implement` and `to-tickets` skills already read it. No CLAUDE.md line is added.
- **Database probe:** a new small interface with one operation that reports whether the database is reachable, plus a short reason when it isn't. The Postgres implementation runs `SELECT 1` through the existing `Database` engine, with a short connect timeout. It turns DNS failures, refused connections and timeouts into "unreachable" with a reason, and never includes the connection URL.
- **`create_app`** takes the database probe as a third collaborator, alongside the tender lookup and the document storage, following the existing constructor-injection pattern.
- **`GET /health` contract:** reachable → 200 `{"database": "ok"}`. Unreachable → 503 `{"database": "unreachable", "reason": "<short reason>"}`. The response carries no other fields, and the endpoint doesn't touch document storage.
- **Startup:** the API entrypoint calls the probe once before serving and logs a single warning line when the database is unreachable. It then starts the server anyway.
- **The run skill** is a project skill under `.claude/skills/run/`. Its description triggers on running or starting the app and on "backend not running". Its body gives the API command, the UI dev-server command, where the logs go, the `/health` check, and the Aiven power-off gotcha. Ports, scripts and env var names stay in their config files; the skill only names the commands.
- **Figma pointer:** a "Design source" line is added to the dashboard-design spec. It gives file key `uiafXy2Gqbsu1uK6Vxj9QV` ("BankDash" template), node `105:0` "Transaction" (used for the tender list), and node `78:351` "Main Dashboard" (used for the layout shell). It says to use `get_screenshot` or `get_design_context` on those node ids rather than calling `get_metadata` on the whole page.

## Testing Decisions

- **Good tests here exercise external behaviour only:** the HTTP status and JSON body of `/health`. They don't assert on how the probe is called or on log formatting.
- **One seam: `create_app`, driven through FastAPI's test client** (the same seam as the existing API tests). A fake database probe is injected that is either reachable or unreachable with a given reason. Cases:
  - reachable → 200 with `database: ok`
  - unreachable → 503 with `database: unreachable` and the reason
  - the response never includes the database URL
- **Prior art:** the existing API tests, which build the app with an in-memory tender lookup and local document storage on a temp directory.
- **The real Postgres probe is checked in `integration_tests/`** against the live database, alongside the existing tender-lookup integration check. It's run by hand.
- **The guardrail is verified by running it once:** it passes on the clean tree and fails on a file with a deliberate syntax error. It has no unit tests.
- **The startup log line, the docs change, the run skill and the Figma pointer** have no automated tests.

## Out of Scope

- A hosted CI pipeline (GitHub Actions or similar). The repo has no remote CI today; the pre-commit guardrail comes first.
- `ruff format` enforcement, if the codebase isn't already formatted. A full reformat is its own change.
- A Python type checker (mypy or pyright).
- Migrating off the Aiven free plan. The database-vendor research from the same day is a separate decision.
- A database status indicator in the dashboard UI.
- Making the review agent enforce ticket-status updates, or a mechanical check that a ticket's status changed in the commit that implements it.
- A rule for zsh's "no matches found" error on globs that match nothing.

## Further Notes

- Source: retro of sessions `1bfc7c17` and `d341c3e3` on 2026-11-21.
- `compose.yml` is deleted in the working tree but still tracked. The run skill should describe the Aiven setup that is actually used, and not reference compose unless the operator restores it.
- The uncommitted `core/http.py` change that broke the import was fixed by hand during the run session. Once the guardrail exists, that kind of breakage is caught at commit time.
