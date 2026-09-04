# InnerOS Alpha — Alpaca Trading Agents

InnerOS Alpha is a modular, local-first **paper-trading control plane** for the Alpaca AI Trading Agents Hackathon (Aug 28–Sep 4, 2026).

**Paper only. No live money. No secrets in this repository.**

Public judge console: `https://alpaca.creatorcore.ai/console/`

The product is not a standalone trading bot. It is a detachable InnerOS financial module where an AI strategy agent can propose a structured `TradeIntent`, but deterministic code owns contract selection, risk approval, the server kill switch, duplicate protection, and broker execution.

## Local data sovereignty

InnerOS Alpha is designed as a sovereign financial agent rather than a cloud-hosted trading bot. Alpaca remains the trusted broker and market-data boundary, but strategy reasoning runs on owned local AMD infrastructure through a private vLLM endpoint. After Alpaca market/account context is ingested into a bounded `MarketSnapshot`, the reasoning step stays local.

The LLM never receives broker credentials, never talks to the write-capable Trading API directly, and never has authority to place an order. It can only return a structured intent. Deterministic services then choose the contract, apply risk rules, enforce the kill switch, execute only against Alpaca PAPER when explicitly allowed, and write evidence under the same `correlation_id`.

For judges, this means the demo is not asking them to trust an opaque AI trader. It shows an auditable control plane where local agents can reason, Alpaca can provide live financial context, and deterministic code remains the authority for financial safety.

## Current working spine

```text
Alpaca Market + Account Context
          |
          v
MarketSnapshot
          |
          v
Local Strategy Agent
Private Qwen3-Coder / vLLM
          |
          v
TradeIntent
          |
          v
Deterministic Options Contract Selector
          |
          v
Deterministic Risk Engine
1% trade risk / 3% daily loss / max 4 positions / DTE / stale data / dedupe / kill switch
          |
          v
Execution Agent
Alpaca PAPER Trading API only
          |
          v
Evidence Store + Global Live Trace
same correlation_id end-to-end
```

If local reasoning is unreachable or returns invalid JSON, the system fails closed into `NO_TRADE`. If the broker is not configured, execution is `BLOCKED`. The UI never invents fills or P&L.

## Judge architecture at a glance

- **Market Scout** reads Alpaca market/account context through PAPER-safe runtime adapters.
- **Local Strategy Agent** runs on private Qwen3-Coder/vLLM infrastructure and produces a bounded `TradeIntent`.
- **Options Engineer** deterministically filters Alpaca option-chain candidates.
- **Risk Sentinel** applies portfolio, loss, stale-data, duplicate and kill-switch gates.
- **Execution Agent** is the only component allowed to call the Alpaca Trading API, and only in PAPER mode.
- **Evidence/Audit** persists the decision path, broker response and final state under one `correlation_id`.

The public judge route can be protected by an authenticated InnerOS gateway. Credentials and access tokens belong in protected runtime configuration only; they are never committed to Git or embedded in the public console.

## Alpaca MCP and Trading API

The Trading API is the only write path and is hard-bound to `https://paper-api.alpaca.markets`.

The official Alpaca MCP V2 server is integrated as a **read-only sidecar** using explicit toolsets:

```text
account,assets,stock-data,options-data,news
```

The `trading` MCP toolset is deliberately excluded. The LLM can inspect Alpaca-native context but cannot bypass deterministic contract selection, risk, or the Execution Agent.

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

The FastAPI app mounts the console at `/console/`. For a standalone static preview:

```bash
python3 -m http.server 8099 --directory apps/console
```

## Configuration

Copy `.env.example` to a private runtime environment. Do not commit credentials.

Canonical variables:

- `ALPACA_PAPER=true`
- `ALPACA_PAPER_TRADE=true`
- `ALPACA_API_BASE=https://paper-api.alpaca.markets`
- `ALPACA_API_KEY`
- `ALPACA_SECRET_KEY`
- `ALPACA_TOOLSETS=account,assets,stock-data,options-data,news`
- `INNEROS_REASONING_URL`
- `INNEROS_REASONING_MODEL=QuantTrio/Qwen3-Coder-30B-A3B-Instruct-AWQ`
- `INNEROS_KILL_SWITCH_DEFAULT=true`
- optional `INNEROS_MONGO_URI` for durable evidence

`ALPACA_KEY_ID` remains accepted by the Trading API adapter for backward compatibility, but `ALPACA_API_KEY` is the canonical shared name for Trading API + Alpaca MCP.

The resident strategy model is served through a private OpenAI-compatible vLLM endpoint. Hostnames, LAN addresses and tunnel details remain in untracked runtime configuration rather than the public repository. External paid models are not the default execution path.

## Readiness and API

- `GET /health`
- `GET /ready`
- `GET /api/mcp/status`
- `GET /api/submission/status`
- `GET /api/portfolio`
- `GET /api/market/{ticker}`
- `GET /api/intent/{ticker}`
- `POST /api/risk`
- `POST /api/pipeline/{ticker}?execute=false`
- `GET|POST /api/kill-switch`
- `POST /api/execute`
- `GET /api/trace/{correlation_id}`
- `GET /api/evidence/{correlation_id}`

Mutable broker controls require the server-side `X-InnerOS-Admin-Token` gate. If the gate is not configured, public writes fail closed.

## Controlled PAPER E2E proof

Preflight only. This cannot submit an order:

```bash
python -m src.controlled_paper_e2e SPY
```

The final controlled competition proof requires an explicit flag:

```bash
python -m src.controlled_paper_e2e SPY --confirm-paper-order
```

Before permitting one PAPER pipeline execution, the helper requires:

1. Alpaca PAPER credentials;
2. `PAPER_LIVE` account context;
3. USD 100,000 equity before the first controlled order;
4. the local Qwen runtime and expected model to be available;
5. the server kill switch to start ON.

The helper captures the Alpaca order ID and pipeline `correlation_id`, verifies correlation consistency and evidence persistence, and re-arms the kill switch in `finally`, including exception paths. It never claims a fill or P&L that Alpaca has not returned.

## Tests

```bash
python3 -m compileall -q src tests
python3 -m pytest tests -q
```

Current post-merge validation: **52/52 tests PASS**.

Coverage includes API safety, PAPER-only adapter guards, reasoning fail-closed behavior, deterministic contract/risk logic, correlation-ID integrity, admin write gates, MCP readiness, submission readiness, controlled PAPER E2E kill-switch recovery, and public-repository hygiene.

## InnerOS module contract

`inneros.module.json` describes the portable module entrypoints, permissions, capabilities, agents, connectors, and security requirements. The intended host path is an authenticated InnerOS Module Gateway; the standalone console remains available for hackathon/demo use.

## Repository layout

```text
apps/console/                responsive paper-trading console
src/main.py                  FastAPI surface
src/reasoning.py             local Qwen strategy adapter
src/contracts.py             deterministic options selector
src/risk.py                  deterministic risk gates
src/alpaca_adapter.py        PAPER-only Alpaca adapter
src/pipeline.py              orchestrated pipeline + trace
src/controlled_paper_e2e.py  one-command final PAPER proof
src/evidence.py              memory/Mongo evidence store
mcp/                         official Alpaca MCP integration config
inneros.module.json          detachable InnerOS module manifest
tests/                       safety and contract regressions
```
