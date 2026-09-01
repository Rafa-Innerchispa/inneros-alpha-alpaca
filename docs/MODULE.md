# InnerOS Alpha Alpaca module

This branch integrates the Codex paper backend with the Cursor portable console without touching InnerOS core.

## Boundaries

| Path | Role |
|---|---|
| `apps/console/**` | Portable UI/module shell |
| `inneros.module.json` | InnerOS Module Gateway manifest |
| `src/inneros_alpha_alpaca/**` | FastAPI paper backend |
| `tests/**` | Backend contracts/risk/API tests |

## Truth contract

- Real money is forbidden.
- The UI never invents fills or P&L.
- `FIXTURE` means display/demo data only.
- `INNEROS` means data returned by the local backend.
- `ALPACA_PAPER` requires backend evidence from the Alpaca paper path.
- A PASS execution with `alpaca_order_id` and `source=ALPACA_PAPER` may be shown as a verified paper execution.
- Missing evidence stays `NO_TRADE`, `BLOCKED`, or `FAIL`.

## Standalone demo

Backend:

```bash
uvicorn inneros_alpha_alpaca.app:app --app-dir src --host 127.0.0.1 --port 8080
```

Console:

```bash
python3 -m http.server 8099 --directory apps/console
```

Open `http://127.0.0.1:8099/?api=http://127.0.0.1:8080`.
Without `?api=...`, the UI deliberately stays in `FIXTURE` mode.

## Embedded mode

`?embed=1&host_origin=https://inneros.example&back=https://inneros.example/app`

When `require_gateway=1` is present, a `module_token` is required or the module shows `BLOCKED`. `host_origin` alone never satisfies the gateway requirement.

## API contract

- `GET /health` must report `ok=true` and `paper_only=true`.
- `GET /api/session` supplies correlation-aware market/execution state.
- `POST /api/intents/evaluate` runs deterministic risk.
- `POST /api/orders/paper` is backend-only and remains guarded by paper credentials and risk decisions.
- The browser console does not auto-submit orders.
