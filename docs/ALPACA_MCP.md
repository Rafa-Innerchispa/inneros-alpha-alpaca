# Alpaca MCP integration

InnerOS Alpha Alpaca is paper-only. The backend refuses live trading and keeps
credentials out of the repository.

Official Alpaca guidance says the MCP server can expose Trading and Market Data
tools to MCP clients and is commonly launched with:

```bash
uvx alpaca-mcp-server
```

For this project, configure only paper trading credentials in the runtime
environment:

```bash
ALPACA_PAPER=true
ALPACA_API_BASE=https://paper-api.alpaca.markets
ALPACA_KEY_ID=...
ALPACA_SECRET_KEY=...
```

The backend adapter uses `https://paper-api.alpaca.markets/v2/orders` only when
the risk engine passes and credentials are present. Without credentials, it
returns `NO_TRADE` with explicit evidence instead of inventing a fill.

Sources checked on 2026-09-01:
- https://docs.alpaca.markets/us/docs/alpaca-mcp-server
- https://docs.alpaca.markets/us/docs/paper-trading
- https://docs.alpaca.markets/us/reference/postorder
