# InnerOS Alpha Sovereignty Architecture

InnerOS Alpha separates financial intelligence from financial authority. The AI can reason about market context, but deterministic code controls contract selection, risk approval, kill-switch state, broker execution and evidence.

## Data boundary

Alpaca is the external financial boundary. The system reads Alpaca market, account, options and news context, then converts it into bounded runtime objects for local reasoning. After that point, the strategy analysis runs on owned AMD hardware through a private Qwen3-Coder/vLLM endpoint.

No broker credential, access token or private deployment topology is stored in the repository or returned to the browser.

## Agent roles

- **Market Scout:** gathers live Alpaca market/account context.
- **Quant Analyst:** computes deterministic short-horizon features from Alpaca market bars.
- **Local Strategy Agent:** reasons locally and emits a structured `TradeIntent` with thesis, evidence, invalidation and primary risk.
- **Options Engineer:** filters contracts using deterministic eligibility rules and reports scan counts.
- **Risk Sentinel:** enforces risk limits, stale-data gates, duplicate protection and the kill switch.
- **Execution Agent:** performs the only broker write path, restricted to Alpaca PAPER Trading API.
- **Evidence/Audit:** records trace, inputs, decisions and broker response under one `correlation_id`.

## Alpaca MCP policy

The official Alpaca MCP V2 server is used as a read-only sidecar with explicit toolsets:

```text
account,assets,stock-data,options-data,news
```

The `trading` toolset is intentionally excluded. The LLM may inspect Alpaca-native context, but it cannot bypass the deterministic Execution Agent.

## Judge access boundary

The production judge console is authenticated. Username/password and session material are supplied only from server-side secret storage and are not committed to Git. `/health` remains a minimal public liveness route; console and API surfaces require an authenticated session when `INNEROS_JUDGE_AUTH_REQUIRED=true`.

## Safety posture

- PAPER only; live-money trading is not used.
- Broker writes are behind deterministic risk gates and a server kill switch.
- Public demo analysis uses `execute=false` and never creates a new order.
- Invalid or unavailable local reasoning fails closed into `NO_TRADE`.
- Evidence must be truthful: no fabricated fills, P&L, metrics or profitability claims.
- The canonical PAPER proof and concurrency incident remain documented instead of hidden or rewritten.

## Judge demo path

The judge sees a sovereign opportunity-hunt flow:

1. Alpaca provides live market/account context.
2. Market Scout and Quant Analyst build a bounded evidence packet.
3. Local Qwen returns a thesis, evidence, invalidation and risk.
4. Deterministic services scan the option chain and select the best eligible contract.
5. Risk Sentinel compares proposed max loss with the real PAPER portfolio and policy limits.
6. Execution remains disabled for the public demo, with kill switch governance visible.
7. The final trace shows the same `correlation_id` from market input to evidence.
