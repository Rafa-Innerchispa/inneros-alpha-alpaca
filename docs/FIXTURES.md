# Fixture policy

The paper backend lives on `src.main:app` (`GET /health`, `POST /api/pipeline/{ticker}`).
When that probe fails, the console loads `apps/console/fixtures/session.json`.

Rules:

- Every fixture event has `"source": "FIXTURE"`.
- The UI always shows a **FIXTURE** badge on those rows.
- Kill switch and risk gates can move state to `BLOCKED` / `NO_TRADE` locally.
- The UI never invents a fill, never shows a live order id, never claims PASS
  on an execution that did not happen.
- Live rows only appear after a successful backend response. The console never
  calls `POST /api/execute`.
