# InnerOS Alpha — Alpaca Trading Agents

InnerOS Alpha is a modular, local-first **paper-trading control plane** for the Alpaca AI Trading Agents Hackathon (Aug 28–Sep 4, 2026).

**Paper only. No live money. No secrets in this repository.**

The product is not a standalone trading bot. It is a detachable InnerOS financial module where an AI strategy agent can propose a structured `TradeIntent`, but deterministic code owns risk approval, the server kill switch, duplicate protection, and broker execution.

## Current working spine

```text
Alpaca Market Data / FIXTURE
          |
          v
MarketSnapshot
          |
          v
Local Strategy Agent
AMD .5 / Qwen3-Coder via vLLM
          |
          v
TradeIntent
          |
          v
Deterministic Risk Engine
1% trade risk / 3% daily loss / max 4 positions / DTE / stale data / dedupe / kill switch
          |
          v
Execution Agent
Alpaca PAPER endpoint only
          |
          v
Evidence Store + Global Live Trace
same correlation_id end-to-end
```

If local reasoning is unreachable or returns invalid JSON, the system fails closed into `NO_TRADE`. If the broker is not configured, execution is `BLOCKED`. The UI never invents fills or P&L.

## Truth states

- `LIVE`: connected market or local agent step executed.
- `PAPER_LIVE`: broker action reached Alpaca Paper.
- `FIXTURE`: explicit fallback/demo data.
- `PASS`: deterministic risk gate passed.
- `NO_TRADE`: analysis completed but no trade should be sent.
- `BLOCKED`: a safety/risk/configuration gate prevented execution.
- `FAIL`: a real error occurred.

## Local run

Backend:

```bash
python3 -m uvicorn src.main:app --host 127.0.0.1 --port 8088
```

Console:

```bash
python3 -m http.server 8099 --directory apps/console
```

Open `http://127.0.0.1:8099/`.

The console attempts the backend at `http://127.0.0.1:8088`. Override it with:

```text
http://127.0.0.1:8099/?api=http://HOST:PORT
```

## Configuration

Copy `.env.example` to your private runtime environment. Do not commit credentials.

Important variables:

- `ALPACA_PAPER=true`
- `ALPACA_API_BASE=https://paper-api.alpaca.markets`
- `ALPACA_KEY_ID`
- `ALPACA_SECRET_KEY`
- `INNEROS_REASONING_URL`
- `INNEROS_REASONING_MODEL=QuantTrio/Qwen3-Coder-30B-A3B-Instruct-AWQ`
- `INNEROS_KILL_SWITCH_DEFAULT=true`
- optional `INNEROS_MONGO_URI` for durable evidence

On the AMD .5 node, the resident strategy model is served through the private OpenAI-compatible vLLM endpoint. External paid models are not the default execution path.

## API

- `GET /health`
- `GET /api/portfolio`
- `GET /api/market/{ticker}`
- `GET /api/intent/{ticker}`
- `POST /api/risk`
- `POST /api/pipeline/{ticker}?execute=false`
- `GET|POST /api/kill-switch`
- `POST /api/execute`
- `GET /api/trace/{correlation_id}`
- `GET /api/evidence/{correlation_id}`

## Tests

```bash
python3 -m compileall -q src tests
python3 -m pytest -q
```

The current validation branch has API, risk, adapter, pipeline, reasoning fail-closed, and correlation-ID tests.

## InnerOS module contract

`inneros.module.json` describes the portable module entrypoints, permissions, capabilities, agents, connectors, and security requirements. The intended host path is an authenticated InnerOS Module Gateway; the standalone console remains available for hackathon/demo use.

## Repository layout

```text
apps/console/          responsive paper-trading console
src/main.py            FastAPI surface
src/reasoning.py       local Qwen strategy adapter
src/risk.py            deterministic risk gates
src/alpaca_adapter.py  paper-only Alpaca adapter
src/pipeline.py        orchestrated pipeline + trace
src/evidence.py        memory/Mongo evidence store
inneros.module.json    detachable InnerOS module manifest
tests/                 safety and contract tests
```
