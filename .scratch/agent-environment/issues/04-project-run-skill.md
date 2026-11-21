# 04: Project run skill

**What to build:** When the operator asks an agent to run the project, or says the backend isn't running, a project skill gives the agent the recipe:
- start the API and the UI dev server in the background, with their logs going to the scratchpad
- check `/health`
- if the database is unreachable, explain that the Aiven free plan powers off when idle and must be powered on from the Aiven console

The database comes from `DB_URL` in `.env`; there is no local Postgres or compose file. Ports, scripts and env var names stay in their config files, and the skill names only the commands. Follow the `writing-for-agents` skill for the description and body. Spec: `.scratch/agent-environment/spec.md`.

**Blocked by:** 03 (Database health check)

**Status:** ready-for-agent

- [ ] A project skill exists whose description triggers on running or starting the app and on "backend not running"
- [ ] The skill gives the API and UI start commands, where their logs go, and the `/health` check
- [ ] The skill records the Aiven free-plan power-off gotcha and what to tell the operator
- [ ] The skill doesn't reference the deleted compose file
- [ ] In a fresh session, "run the project" starts both processes and reports health without the agent reading the packaging or Vite config
