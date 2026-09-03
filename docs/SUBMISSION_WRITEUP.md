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

The runtime uses a dedicated Alpaca PAPER competition account. Credentials are injected server-side and are never committed to GitHub or exposed in the public demo.

## Public demo and current evidence

The judge console is publicly available at:

`https://alpaca.creatorcore.ai/console/`

Verified runtime evidence now includes:

- Alpaca PAPER authentication: HTTP 200;
- account status: `ACTIVE`;
- starting cash: USD 100,000;
- starting equity: USD 100,000;
- buying power: USD 400,000;
- `trading_blocked=false`;
- PAPER-only boundary active;
- local AMD Qwen runtime reachable;
- expected Qwen3-Coder model available;
- official Alpaca MCP configured with explicit read-only toolsets;
- deterministic contract selection and risk controls active;
- server-side kill switch begins ON and is re-armed after controlled execution.

The public service is being reloaded to consume the final private runtime environment. Until that reload is reflected by `/ready`, the public endpoint may still report some broker/MCP readiness fields as pending even though the PAPER credentials and controlled E2E proof have already been validated server-side.

## Controlled PAPER proof

The repository includes a fail-closed final proof command:

```bash
python -m src.controlled_paper_e2e SPY
```

Without an explicit confirmation flag this performs preflight only and cannot submit an order. The controlled judge proof uses:

```bash
python -m src.controlled_paper_e2e SPY --confirm-paper-order
```

Before permitting that one PAPER pipeline execution, the helper requires:

1. Alpaca PAPER credentials to be present;
2. the Alpaca account probe to return a live PAPER account;
3. account equity to be USD 100,000 before the first controlled order;
4. the local Qwen runtime to be reachable and the configured model available;
5. the server kill switch to begin ON.

The verified run then disarmed the kill switch only for the controlled call, executed Market -> Strategy -> Contract -> Risk -> Execution -> Evidence with one correlation ID, persisted evidence, captured Alpaca's returned order ID and re-armed the kill switch in `finally`.

### Verified PAPER E2E evidence

- Pre-trade account: **ACTIVE PAPER account, USD 100,000 cash/equity**
- Local reasoning model: **QuantTrio/Qwen3-Coder-30B-A3B-Instruct-AWQ**
- Selected option contract: **SPY260930C00779000**
- Risk decision: **PASS**
- Execution state: **submitted**
- Alpaca PAPER order ID: **6e1cc1de-821c-49e1-8605-c8161caf1a05**
- Pipeline correlation ID: **8006ee08-104a-4bcc-91c7-1013ae4b1a41**
- Correlation consistency: **verified**
- Evidence persistence: **verified**
- Kill switch after run: **ON / re-armed**
- Live-money trading: **never used**

## Evidence and demo

The console exposes truthful states such as `PAPER_LIVE`, `FIXTURE`, `NO_TRADE`, `BLOCKED` and `FAIL`. It never fabricates fills or P&L. The final demo shows the architecture, local AI strategy intent, contract selection, risk gates, the controlled PAPER execution, Alpaca's returned order ID and the matching evidence trace.

### Final submission status

- Competition account initial USD 100,000 verification: **VERIFIED**
- Controlled PAPER order ID: **VERIFIED**
- Deterministic risk decision: **VERIFIED PASS**
- Evidence trace and kill-switch re-arm: **VERIFIED**
- Final strategy P&L: **not claimed unless returned by Alpaca/competition results**
- Public service final readiness reload: **IN PROGRESS**
- Demo video: **PENDING FINAL RECORDING**
- Pitch deck: **PENDING FINAL EXPORT / UPLOAD**
