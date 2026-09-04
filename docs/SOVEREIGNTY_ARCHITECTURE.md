# InnerOS Alpha Sovereignty Architecture

InnerOS Alpha separates financial intelligence from financial authority. The AI can reason about market context, but deterministic code controls contract selection, risk approval, kill-switch state, broker execution and evidence.

## Data boundary

Alpaca is the external financial boundary. The system reads Alpaca market, account, options and news context, then converts it into bounded runtime objects for local reasoning. After that point, the strategy analysis runs on owned AMD hardware through a private Qwen3-Coder/vLLM endpoint.

No broker credential, access token or private deployment topology is stored in the repository or returned to the browser.

## Agent roles

- **Market Scout:** gathers live Alpaca market/account context.
- **Local Strategy Agent:** reasons locally and emits a structured `TradeIntent`.
- **Options Engineer:** filters contracts using deterministic eligibility rules.
- **Risk Sentinel:** enforces risk limits, stale-data gates, duplicate protection and the kill switch.
- **Execution Agent:** performs the only broker write path, restricted to Alpaca PAPER Trading API.
- **Evidence/Audit:** records trace, inputs, decisions and broker response under one `correlation_id`.

## Alpaca MCP policy

The official Alpaca MCP V2 server is used as a read-only sidecar with explicit toolsets:

```text
account,assets,stock-data,options-data,news
```

The `trading` toolset is intentionally excluded. The LLM may inspect Alpaca-native context, but it cannot bypass the deterministic Execution Agent.

## Safety posture

- PAPER only; live-money trading is not used.
- Broker writes are behind deterministic risk gates and a server kill switch.
- Invalid or unavailable local reasoning fails closed into `NO_TRADE`.
- Evidence must be truthful: no fabricated fills, P&L, metrics or profitability claims.
- The canonical PAPER proof and concurrency incident remain documented instead of hidden or rewritten.

## Judge demo path

The judge should see a sovereign opportunity-hunt flow:

1. Alpaca provides live market/account context.
2. Local Qwen returns a bounded strategy thesis.
3. Deterministic services select and risk-check an options contract.
4. The execution gate remains PAPER-only and kill-switch governed.
5. The final trace shows the same `correlation_id` from market input to evidence.
