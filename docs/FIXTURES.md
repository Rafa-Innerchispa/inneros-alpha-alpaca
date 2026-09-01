# Fixture policy

Until Codex lands a paper backend, the console loads
`apps/console/fixtures/session.json`.

Rules:

- Every fixture event has `"source": "FIXTURE"`.
- The UI always shows a **FIXTURE** badge on those rows.
- Kill switch and risk gates can move state to `BLOCKED` / `NO_TRADE` locally.
- The UI never invents a fill, never shows a live order id, never claims PASS
  on an execution that did not happen.
- When the backend exists, replace the fixture fetch with
  `GET /api/session?correlation_id=...` and drop the badge only for real events.
