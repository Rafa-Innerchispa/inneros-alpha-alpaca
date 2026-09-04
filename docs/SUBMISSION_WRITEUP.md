# InnerOS Alpha: Sovereign Multi-Agent Trading Control Plane

## What we built

InnerOS Alpha is a PAPER-only multi-agent trading control plane for the Alpaca AI Trading Agents Hackathon. The core idea is simple: **the AI may propose, but policy owns the final authority.**

The system combines local AI reasoning with deterministic financial controls so an LLM can analyze a live opportunity without ever receiving broker credentials or unrestricted order authority.

The end-to-end path is:

**Alpaca live market/account context -> Market Scout + Quant Analyst -> local Qwen thesis -> deterministic option contract selector -> deterministic risk engine -> execution gate -> evidence trace.**

Every stage carries the same `correlation_id`, producing a judge-visible chain from live market evidence to the final no-write decision.

## Local data sovereignty

InnerOS Alpha is designed as a sovereign financial-agent system rather than a cloud-hosted trading bot.

- Alpaca is the external broker and market-data boundary.
- Strategy reasoning runs on owned AMD infrastructure through private Qwen3-Coder/vLLM.
- After Alpaca data is ingested into bounded runtime objects, reasoning remains local.
- The local model receives market evidence, not broker credentials.
- The official Alpaca MCP server is restricted to read-only toolsets.
- Deterministic services retain contract, risk and execution authority.
- Judge credentials and runtime secrets remain server-side and never enter Git.

This makes InnerOS Alpha useful beyond one trade. It demonstrates how financial agents can preserve data custody and operator control while still connecting to a regulated financial API.

## Sovereign Opportunity Hunt

The public judge console turns the pipeline into an observable activity instead of a black-box AI answer.

1. **Market Scout** reads the latest Alpaca trade and current PAPER portfolio.
2. **Quant Analyst** requests recent Alpaca bars and computes short-horizon returns such as 5m, 15m and 60m when available.
3. **Local Qwen Strategy Agent** receives that bounded evidence and returns directional bias, confidence, thesis, supporting evidence, invalidation and primary risk.
4. **Options Engineer** queries real Alpaca option candidates, counts how many contracts were scanned and how many passed DTE, strike, spread, quote and tradability gates.
5. **Risk Sentinel** compares the selected contract's estimated max loss against real PAPER account equity, open positions, daily P&L and deterministic policy limits.
6. **Execution Gate** remains blocked in the public demo because the call uses `execute=false` and the server kill switch remains ON.
7. **Evidence/Audit** records the entire path under one correlation ID.

The judge therefore sees not only what the AI proposed, but what data it used, what contract deterministic code selected, what risk was measured and why execution is or is not allowed.

## Alpaca infrastructure

The project uses Alpaca's Trading API for PAPER account/position reads and controlled PAPER order execution. Non-paper endpoints are rejected by code.

It also integrates Alpaca's official MCP V2 server as a **read-only sidecar** with explicit toolsets:

`account, assets, stock-data, options-data, news`

The `trading` toolset is deliberately excluded. The LLM can inspect Alpaca-native context without gaining an alternate broker-write path.

## Deterministic risk controls

The LLM cannot bypass the Risk Engine. Current gates include:

- maximum risk per trade: 1% of portfolio equity;
- daily loss cap: 3%;
- maximum four open positions;
- option DTE window: 14-45 days;
- stale market-data rejection;
- duplicate-intent protection;
- option quote/spread/tradability filters;
- correlation consistency;
- server-side kill switch.

If local reasoning is unavailable or invalid, the system fails closed into `NO_TRADE`.

## Secure judge access

The production judge console uses username/password authentication with session cookies. Credentials are injected from protected runtime secret storage, not committed to Git or embedded in the browser. `/health` remains a minimal public liveness endpoint while the judge console and API require an authenticated session when production auth is enabled.

## Canonical PAPER proof

A controlled PAPER end-to-end run was already completed and is preserved as historical evidence. The public demo does not create another order.

- verified initial competition baseline: **USD 100,000 equity/cash**
- local model: **QuantTrio/Qwen3-Coder-30B-A3B-Instruct-AWQ**
- selected contract: **SPY260930C00779000**
- risk decision: **PASS**
- canonical Alpaca PAPER order ID: **6e1cc1de-821c-49e1-8605-c8161caf1a05**
- canonical correlation ID: **8006ee08-104a-4bcc-91c7-1013ae4b1a41**
- evidence persistence: **verified**
- kill switch after proof: **ON / re-armed**
- live-money trading: **never used**

A later overlapping agent session produced a second PAPER submission before the execution lane was frozen. That incident is documented rather than hidden and is not used as the canonical proof. It reinforces the governance problem InnerOS is designed to solve.

## Judge framing

**Problem:** financial AI agents often blur data custody, model authority and broker execution.

**Solution:** InnerOS Alpha keeps reasoning local, Alpaca access bounded, risk deterministic and broker authority outside the LLM.

**Differentiator:** local data sovereignty + read-only Alpaca MCP + deterministic contract/risk authority + auditable correlation trace.

**Proof:** live opportunity analysis uses current Alpaca context with `execute=false`, while a separate historical replay exposes the previously verified PAPER E2E evidence.

**Safety:** PAPER only, kill switch ON, no profitability claim, no fabricated fills or P&L.

## Public demo

`https://alpaca.creatorcore.ai/console/`

## Repository

`https://github.com/Rafa-Innerchispa/inneros-alpha-alpaca`
