# 01: Ruff config and clean baseline

**What to build:** Ruff's rules are written down in the project's packaging config: the default rule set plus import sorting, targeting the project's Python version. The virtualenv, `node_modules`, `.scratch` and the vector store are excluded. The existing lint errors (61 at the time of the retro) are fixed, so `ruff check` passes on the whole repo. This is the prefactor that lets the pre-commit check be turned on without blocking unrelated work. Spec: `.scratch/agent-environment/spec.md`.

**Blocked by:** None (can start immediately)

**Status:** done

- [x] Ruff configuration lives in the project's packaging config, with the rule set and exclusions above
- [x] `ruff check` reports zero errors on the whole repo
- [x] Fixes that change behaviour (not just style or imports) are called out in the commit message
- [x] Unit tests still pass
- [x] Record whether `ruff format --check` passes as-is (this decides whether the pre-commit check includes it)

## Comments

- `ruff format --check` does **not** pass as-is: 44 files would be reformatted (ruff 0.16.7). Ticket 02's guardrail should leave the format check out for now.
- The baseline was 60 errors on ruff 0.16.7. Its default rule set already includes UP/BLE/DTZ/RUF/C4/PYI, so the config only adds `I` via `extend-select`.
