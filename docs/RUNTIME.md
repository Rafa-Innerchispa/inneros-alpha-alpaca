# Runtime plan: Intel .4 API + private Qwen tunnel to AMD .5

InnerOS Alpha supports two local-first topologies without exposing the resident Qwen model on the LAN.

## Preferred current topology

Run the FastAPI/UI service on Intel node `192.168.1.4` and keep Qwen3-Coder on AMD node `192.168.1.5`.

The AMD vLLM service remains bound to `127.0.0.1:8000`. Intel already has a private SSH forward on `127.0.0.1:18000`; a verified probe from the registered project runtime reached `/v1/models` through that tunnel and returned `QuantTrio/Qwen3-Coder-30B-A3B-Instruct-AWQ`.

Use `deploy/inneros-alpha-primary.service` on Intel. It reuses the managed InnerOS Python environment and points reasoning to `http://127.0.0.1:18000/v1`, avoiding a second project venv and avoiding LAN exposure of vLLM.

## AMD direct topology

`deploy/inneros-alpha.service` remains available when the API is intentionally hosted on AMD .5. In that topology the API reaches Qwen directly at `http://127.0.0.1:8000/v1` and uses a project-local `.venv`.

## Single-service surface

`uvicorn src.main:app --host 0.0.0.0 --port 8088` serves both:

- API: `/health`, `/ready`, `/api/*`
- UI: `/console/`

The browser therefore uses the same origin by default. The console never calls `/api/execute`; only the server-side pipeline can reach execution after deterministic contract selection, deterministic risk, and the server kill switch.

## Safe activation order on Intel .4

1. Reconcile the registered project checkout to GitHub `main`.
2. Verify `http://127.0.0.1:18000/v1/models` contains `QuantTrio/Qwen3-Coder-30B-A3B-Instruct-AWQ`.
3. Copy `deploy/runtime.env.example` to `~/.config/inneros-alpha/runtime.env` and inject Alpaca PAPER credentials server-side. Never commit or print them.
4. Install `deploy/inneros-alpha-primary.service` as the systemd user unit `inneros-alpha.service`.
5. Start the service and verify `/health`.
6. Verify `/ready` reports `analysis_ready=true`. Until PAPER credentials work, `paper_path_ready=false` is expected.
7. Once PAPER credentials are present, verify `paper_api_reachable=true` while kill switch remains ON.
8. Run analysis-only pipeline and inspect one correlation ID across Market → Strategy → Contract → Risk → Execution → Evidence.
9. Only for a controlled PAPER test, disarm the server kill switch and call the server pipeline with `execute=true`. Re-arm immediately after the test.

## Truth rules

- No credentials: explicit FIXTURE / NO_TRADE, never fake PAPER evidence.
- Qwen unavailable or invalid: NO_TRADE.
- No eligible option contract: NO_TRADE.
- Risk gate or kill switch: BLOCKED.
- Alpaca PAPER accepted order: PAPER_LIVE / submitted.
- Real-money endpoint: process refuses to start.
