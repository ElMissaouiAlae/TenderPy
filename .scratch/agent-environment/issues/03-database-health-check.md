# 03: Database health check

**What to build:** The operator can tell "backend down" from "database down" with one request. `GET /health` returns 200 `{"database": "ok"}` when the database answers. When it doesn't, it returns 503 `{"database": "unreachable", "reason": "<short reason>"}` within a few seconds, including when the host doesn't resolve (the Aiven free-plan power-off case). The API logs one warning line at startup when the database is unreachable, and still starts. `create_app` takes a database probe as a third collaborator. The Postgres probe runs `SELECT 1` with a short connect timeout and never exposes the connection URL. Spec: `.scratch/agent-environment/spec.md`.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] `create_app` accepts a database probe alongside the tender lookup and the document storage
- [ ] API test: with a reachable fake probe, `GET /health` returns 200 `{"database": "ok"}`
- [ ] API test: with an unreachable fake probe, `GET /health` returns 503 with `database: unreachable` and the reason
- [ ] API test: the health response never contains the database URL or credentials
- [ ] The Postgres probe reports unreachable, with a reason, on DNS failure, connection refused and timeout, and returns within a few seconds
- [ ] An integration check runs the Postgres probe against the live database, alongside the existing tender-lookup integration check
- [ ] `python -m api` logs one warning line at startup when the database is unreachable, and still serves `/docs` and `/health`
