# InnerOS Alpha: Sovereign Multi-Agent Trading Control Plane

## What we built

InnerOS Alpha is a PAPER-only multi-agent trading control plane designed for the Alpaca AI Trading Agents Hackathon. The system combines local AI reasoning with deterministic financial controls so an LLM can propose a trade idea without ever receiving authority to bypass risk policy or directly send an order.

The end-to-end path is:

**Alpaca market/account context -> Qwen strategy intent -> deterministic option contract selector -> deterministic risk engine -> Execution Agent -> Alpaca Trading API PAPER -> evidence trace.**

Every stage carries the same `correlation_id`, making a judge-visible decision trace from market data through the final broker result.

## AI logic

The Strategy Agent uses a local Qwen3-Coder model served on our AMD GPU infrastructure. The model receives a bounded market snapshot and returns a structured `TradeIntent`: underlying, directional bias, confidence, option type and rationale. The model does not choose an arbitrary broker order and cannot override a rejection.

If the local reasoning service is unavailable, malformed or uncertain, the pipeline fails closed into `NO_TRADE` rather than inventing a decision. This local-first architecture keeps reasoning cost controlled and makes the model replaceable without changing the deterministic trading boundary.

## Options and contract selection

Every executable strategy uses options. After the AI proposes direction, a deterministic Contract Selector evaluates the Alpaca option chain. It filters contracts by option type, expiration window, tradability, quote validity, spread/liquidity and delta when Greeks are available. It selects a bounded contract and calculates maximum premium risk before the Risk Engine evaluates the trade.

If no suitable contract exists, the system returns `NO_TRADE`.

## Deterministic risk controls

The LLM cannot bypass the Risk Engine. Current gates include:

- maximum risk per trade: 1% of portfolio equity;
- daily loss cap: 3%;
- maximum four open positions;
- option DTE window: 14-45 days;
- stale market-data rejection;
- duplicate-intent/order protection;
- spread/liquidity checks;
- correlation consistency;
- server-side kill switch.

A rejected trade never reaches the broker adapter.

## Alpaca infrastructure

The project uses Alpaca's Trading API for PAPER account/position reads and controlled PAPER order execution. Non-paper endpoints are rejected by code.

It also integrates Alpaca's official MCP V2 server (`uvx alpaca-mcp-server`) as a read-only agent sidecar. The MCP toolsets are explicitly limited to `account,assets,stock-data,options-data,news`. `trading` and other write-capable toolsets are deliberately excluded. This gives the agents Alpaca-native context without granting the LLM an alternate route around the deterministic Execution Agent.

The runtime declares a dedicated Alpaca PAPER competition account. Its credentials are designed to be injected server-side and never committed to GitHub. The required initial USD 100,000 balance remains a live verification item until the competition API credentials are present and the account probe succeeds.

## Public demo and current evidence

The judge console is publicly available at:

`https://alpaca.creatorcore.ai/console/`

The public `/ready` endpoint currently proves the parts that do not require broker credentials:

- `code_ready=true`;
- PAPER-only boundary active;
- local AMD Qwen runtime reachable;
- expected Qwen3-Coder model available;
- official Alpaca MCP configured with explicit read-only toolsets;
- dedicated competition account identity declared server-side;
- write-up finalized;
- kill switch ON.

Until the PAPER API keys are injected, the runtime deliberately reports `paper_path_ready=false`, `mcp_live_ready=false` and `submission_ready=false`. Market analysis may use an explicitly labelled `FIXTURE`; fills and P&L are never fabricated.

## Controlled PAPER proof

The repository includes a fail-closed final proof command:

```bash
python -m src.controlled_paper_e2e SPY
```

Without an explicit confirmation flag this performs preflight only and cannot submit an order. The final judge run uses:

```bash
python -m src.controlled_paper_e2e SPY --confirm-paper-order
```

Before permitting that one PAPER pipeline execution, the helper requires:

1. Alpaca PAPER credentials to be present;
2. the Alpaca account probe to return `PAPER_LIVE`;
3. account equity to be USD 100,000 before the first controlled order;
4. the local Qwen runtime to be reachable and the configured model available;
5. the server kill switch to begin ON.

It then disarms the kill switch only for the controlled call, runs Market -> Strategy -> Contract -> Risk -> Execution -> Evidence with one correlation ID, captures the returned Alpaca order ID if submitted, and re-arms the kill switch in `finally` even if execution raises.

## Evidence and demo

The console exposes truthful states such as `PAPER_LIVE`, `FIXTURE`, `NO_TRADE`, `BLOCKED` and `FAIL`. It never fabricates fills or P&L. The final demo will show MCP/account readiness, market and options data, Qwen's structured intent, contract selection, risk gates, a controlled PAPER execution, Alpaca's returned order ID and the matching evidence trace.

### Final live evidence

- Competition account initial USD 100,000 verification: **PENDING LIVE PROBE**
- Controlled PAPER order ID: **PENDING LIVE E2E**
- Final strategy P&L: **PENDING COMPETITION RESULT**
- Demo video: **PENDING FINAL RECORDING**

These fields remain explicitly pending until real Alpaca PAPER evidence exists.
