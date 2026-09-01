# Alpaca as a detachable InnerOS module

Cursor owns `apps/console/` + `inneros.module.json`.
Codex owns `src/` on `codex/alpaca-backend-spine-20260901`. This branch does **not** merge or edit that spine.

## Boundaries

| Path | Owner | Notes |
|---|---|---|
| `apps/console/**` | Cursor | Portable module shell |
| `inneros.module.json` | Cursor | Gateway manifest |
| `src/inneros_alpha_alpaca/**` | Codex | Paper FastAPI spine |
| Judge / InnerOS fabric | frozen / Codex | Do not touch |

## Standalone demo

```bash
python3 -m http.server 8099 --directory apps/console
```

http://127.0.0.1:8099/ loads fixtures. Query `?api=http://127.0.0.1:8080` to probe Codex `/health` + `/api/session` **without submitting orders**.

## Embedded later

`?embed=1&host_origin=https://inneros.example&back=https://inneros.example/app`
`?embed=1&require_gateway=1` without token → `BLOCKED`.

The module posts `inneros.module.ready` to `host_origin` when framed.

## Client contract (matches Codex branch, unread-only)

- `GET /health` must be `{ ok: true, paper_only: true }`
- `GET /api/session`
- `POST /api/intents/evaluate`
- Console **never** calls `POST /api/orders/paper` (kill switch + no fake fills)

If health/session fail, UI stays on **FIXTURE** and says so.
