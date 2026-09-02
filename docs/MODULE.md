# Alpaca as a detachable InnerOS module

Cursor owns `apps/console/` + this document + embed/nav chrome.
The paper backend in `src/` already lives on `main` (`src.main:app`). **Do not rewrite `src/` on this Cursor branch.**

## Boundaries

| Path | Owner | Notes |
|---|---|---|
| `apps/console/**` | Cursor | Portable module shell, FIXTURE fallback |
| `inneros.module.json` | shared | Gateway manifest; paper-only |
| `src/**` | Codex / local-agent on `main` | FastAPI paper pipeline |
| Judge / InnerOS fabric | frozen / Codex | Do not touch |

## Standalone demo

```bash
python3 -m uvicorn src.main:app --host 127.0.0.1 --port 8088
python3 -m http.server 8099 --directory apps/console
```

Open http://127.0.0.1:8099/ — console probes `http://127.0.0.1:8088`. Override with `?api=http://HOST:PORT`.

If `/health` fails, the UI loads `apps/console/fixtures/session.json` and keeps the **FIXTURE** badge. It never invents fills or P&L.

## Embedded later

`?embed=1&host_origin=https://inneros.example&back=https://inneros.example/app`

`?embed=1&require_gateway=1` without `module_token` or `host_origin` → **BLOCKED**.

When framed, the module posts `inneros.module.ready` to `host_origin`.

## Client contract (matches `src/main.py` on main)

- `GET /health` → `{ ok: true, paper_only: true }`
- `GET /api/portfolio`
- `POST /api/pipeline/{ticker}?execute=false` (analysis only)
- `GET` / `POST /api/kill-switch`

The console **never** calls `POST /api/execute`. Kill switch + risk engine own broker traffic on the server.
