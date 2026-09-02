# Runtime plan: private local reasoning + PAPER-only API

InnerOS Alpha is local-first without requiring the resident Qwen model to be exposed on a LAN interface. Deployment-specific hostnames, private IPs, usernames and tunnel ports belong in untracked runtime configuration, not this public repository.

## Supported topology

Run the FastAPI/UI service on an approved private host and keep Qwen3-Coder behind a private OpenAI-compatible vLLM endpoint. The public examples default to loopback:

```text
INNEROS_REASONING_URL=http://127.0.0.1:8000/v1
```

If the API and model live on different private hosts, configure a private tunnel outside the repository and set `INNEROS_REASONING_URL` only in `~/.config/inneros-alpha/runtime.env`.

Use `deploy/inneros-alpha-primary.service` for the primary-host pattern. `deploy/inneros-alpha.service` remains a minimal project-local-venv example. Neither file contains account identity, credentials or deployment-specific LAN topology.

## Single-service surface

`uvicorn src.main:app --host 127.0.0.1 --port 8088` serves both:

- API: `/health`, `/ready`, `/api/*`
- UI: `/console/`

For public demo access, terminate TLS/proxying outside the application and forward only to the local service. The console never calls `/api/execute`; mutable execution controls require the server-side admin gate, deterministic contract selection, deterministic risk, and the server kill switch.

## Safe activation order

1. Reconcile the registered project checkout to GitHub `main`.
2. Verify `${INNEROS_REASONING_URL}/models` contains `QuantTrio/Qwen3-Coder-30B-A3B-Instruct-AWQ`.
3. Copy `deploy/runtime.env.example` to `~/.config/inneros-alpha/runtime.env` and inject Alpaca PAPER credentials server-side. Never commit or print them.
4. Install the chosen example as the systemd user unit `inneros-alpha.service`.
5. Start the service and verify `/health`.
6. Verify `/ready` reports `analysis_ready=true`. Until PAPER credentials work, `paper_path_ready=false` is expected.
7. Once PAPER credentials are present, verify `paper_api_reachable=true` while the kill switch remains ON.
8. Run `python -m src.controlled_paper_e2e SPY` for preflight only.
9. Only after account equity is verified at USD 100,000, run `python -m src.controlled_paper_e2e SPY --confirm-paper-order` for the single controlled PAPER proof. The helper re-arms the kill switch in `finally`.

## Truth rules

- No credentials: explicit FIXTURE / NO_TRADE, never fake PAPER evidence.
- Qwen unavailable or invalid: NO_TRADE.
- No eligible option contract: NO_TRADE.
- Risk gate or kill switch: BLOCKED.
- Alpaca PAPER accepted order: PAPER_LIVE / submitted.
- Real-money endpoint: process refuses to start.
