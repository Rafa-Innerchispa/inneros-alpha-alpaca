# Runtime plan: AMD .5

InnerOS Alpha is intended to run on AMD node `192.168.1.5` so the API and the resident Qwen3-Coder vLLM service share loopback. This avoids exposing the model port on the LAN and avoids an SSH tunnel from the Intel node.

## Single-service surface

`uvicorn src.main:app --host 0.0.0.0 --port 8088` serves both:

- API: `/health`, `/ready`, `/api/*`
- UI: `/console/`

The browser therefore uses the same origin by default. The console never calls `/api/execute`; only the server-side pipeline can reach execution after deterministic contract selection, deterministic risk, and the server kill switch.

## Safe activation order

1. Reconcile AMD project checkout to GitHub `main`.
2. Create project `.venv` and install `requirements.txt`.
3. Copy `deploy/runtime.env.example` to `~/.config/inneros-alpha/runtime.env` and inject Alpaca PAPER credentials server-side. Never commit or print them.
4. Validate `http://127.0.0.1:8000/v1/models` contains `QuantTrio/Qwen3-Coder-30B-A3B-Instruct-AWQ`.
5. Install `deploy/inneros-alpha.service` as the systemd user unit `inneros-alpha.service`.
6. Start service and verify `/health`.
7. Verify `/ready` reports `analysis_ready=true`. Until PAPER credentials work, `paper_path_ready=false` is expected.
8. Once PAPER credentials are present, verify `paper_api_reachable=true` while kill switch remains ON.
9. Run analysis-only pipeline and inspect one correlation ID across Market → Strategy → Contract → Risk → Execution → Evidence.
10. Only for a controlled PAPER test, disarm the server kill switch and call the server pipeline with `execute=true`. Re-arm immediately after the test.

## Truth rules

- No credentials: explicit FIXTURE / NO_TRADE, never fake PAPER evidence.
- Qwen unavailable or invalid: NO_TRADE.
- No eligible option contract: NO_TRADE.
- Risk gate or kill switch: BLOCKED.
- Alpaca PAPER accepted order: PAPER_LIVE / submitted.
- Real-money endpoint: process refuses to start.
