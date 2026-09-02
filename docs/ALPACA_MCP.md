# Alpaca MCP hackathon contract

InnerOS Alpha uses Alpaca's official Trading MCP Server as a **read-only agent sidecar** and Alpaca's Trading API as the only order-execution transport.

## Why the split matters

The hackathon requires Alpaca's Trading API plus either Alpaca's MCP Server or CLI, and every strategy must include options. The project satisfies that requirement without giving the LLM an unrestricted trading tool.

- **MCP sidecar:** account context, assets, stock data, options data and news.
- **Strategy/Qwen:** proposes structured intent only.
- **Contract selector:** deterministically chooses an option contract.
- **Risk engine:** owns stale-data, DTE, spread/liquidity, duplicate, sizing, daily-loss and kill-switch gates.
- **Execution Agent:** alone may submit a PAPER order through the Trading API.
- **Evidence:** correlation IDs connect market -> strategy -> contract -> risk -> execution.

## Official MCP V2 configuration

The current Alpaca documentation runs the server with `uvx alpaca-mcp-server`. Alpaca defaults `ALPACA_PAPER_TRADE` to `true`, but this project sets it explicitly. Alpaca also defaults `ALPACA_TOOLSETS` to all tools, which includes trading, so InnerOS Alpha **must** set an explicit read-only toolset.

Use `mcp/alpaca.mcp.json.example` as the public template. Credentials are injected server-side only.

Required non-secret settings:

```text
ALPACA_PAPER_TRADE=true
ALPACA_TOOLSETS=account,assets,stock-data,options-data,news
```

`trading` and `watchlists` are intentionally excluded from the agent sidecar because they expose write-capable operations. Paper orders remain behind the project's deterministic Execution Agent.

## Readiness contract

`src/mcp_readiness.py` fails closed when any of these are true:

1. `ALPACA_PAPER_TRADE=false`.
2. `ALPACA_TOOLSETS` is missing, because Alpaca's default is all toolsets.
3. A write-capable toolset such as `trading` or `watchlists` is enabled.
4. `options-data` is absent.
5. Paper API key or secret is missing.

The public readiness payload reports only boolean credential presence. It never returns key values.

## Competition account checklist

Before the first scored PAPER run:

- Dedicated competition Alpaca PAPER account, one email for this hackathon only.
- Starting balance set to **$100,000**.
- Options enabled in the PAPER environment.
- New PAPER API key and secret generated from that dedicated account.
- API credentials stored only in a server-side secret store/runtime environment, never GitHub or chat-visible config.
- One-page submission write-up must explain AI logic, deterministic risk gates, Alpaca Trading API implementation and Alpaca MCP usage.

## Demo proof

The final judge flow should show:

1. MCP readiness = PAPER + read-only + options-data.
2. Account/buying-power read through Alpaca MCP.
3. Option market data/Greeks read through Alpaca MCP or Alpaca market-data API.
4. Qwen strategy intent.
5. Deterministic option contract selection.
6. Risk decision and kill-switch state.
7. PAPER order through the Execution Agent/Trading API only.
8. Alpaca order ID and the same correlation ID in evidence/trace.

No live-money mode is supported by the hackathon runtime.
