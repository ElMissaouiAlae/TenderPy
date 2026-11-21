# 02: Pre-commit check

**What to build:** A checked-in script runs, in order and stopping at the first failure: `ruff check`, `ruff format --check` (only if ticket 01 found the codebase already formatted), the unit tests (not the integration tests, which need the live Aiven database and S3), and the UI typecheck. Git's pre-commit hook calls this script from a tracked hooks directory, and a one-line install step makes the hook live in any clone. The operator can also run the script by hand. Spec: `.scratch/agent-environment/spec.md`.

**Blocked by:** 01 (Ruff config and clean baseline)

**Status:** ready-for-agent

- [ ] One script runs ruff, the unit tests and the UI typecheck, and exits non-zero on the first failure
- [ ] Git's pre-commit hook calls the script; the install step is documented where the run skill or README will find it
- [ ] Committing the clean tree succeeds
- [ ] Committing a Python file with a deliberate syntax error is rejected, and the output names the file and line
- [ ] The check runs offline, while the database is unreachable
- [ ] No new Python dependency is added (no `pre-commit` framework)
