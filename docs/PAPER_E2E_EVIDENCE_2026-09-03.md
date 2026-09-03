# Alpaca PAPER E2E evidence — 2026-09-03

This document records the sanitized execution evidence used for hackathon submission. It contains no API credentials, competition-account identity, private network topology or live-money capability.

## Verified pre-trade baseline

Before the first controlled submission, the dedicated Alpaca PAPER account was verified directly against the PAPER Trading API:

- HTTP 200
- account status `ACTIVE`
- currency `USD`
- cash `100000`
- equity `100000`
- buying power `400000`
- `trading_blocked=false`

This USD 100,000 state is the historical competition baseline. Later equity changes must not be used to overwrite the verified starting state.

## Canonical controlled PAPER proof

The canonical judge proof completed the bounded pipeline:

`Market -> Strategy -> Contract -> Risk -> Execution -> Evidence`

Evidence:

- local reasoning model: `QuantTrio/Qwen3-Coder-30B-A3B-Instruct-AWQ`
- selected option contract: `SPY260930C00779000`
- deterministic risk result: `PASS`
- execution state: `submitted`
- Alpaca PAPER order ID: `6e1cc1de-821c-49e1-8605-c8161caf1a05`
- pipeline correlation ID: `8006ee08-104a-4bcc-91c7-1013ae4b1a41`
- correlation consistency: verified
- evidence persistence: verified
- kill switch after execution: ON / re-armed
- live-money trading: never used

No fill or P&L is claimed unless Alpaca returns authoritative evidence for it.

## Concurrency incident

During final multi-agent orchestration, another agent session entered the already-proven PAPER E2E task after the repository lock expired. Coordination later recorded:

- second Alpaca PAPER order ID: `4db365ec-35fc-48a3-a7f2-72cb645aad20`
- second correlation ID: `ee10b80b-e2bf-462a-a1d6-c9b4ec56b966`

After the final runtime reload, the public PAPER portfolio endpoint confirmed:

- `source=PAPER_LIVE`
- equity `100164.94`
- cash `98961.94`
- buying power `395847.76`
- open positions `2`
- kill switch remained ON through readiness checks

The two open positions are consistent with two submitted PAPER executions. The second submission is not used as the canonical judge proof. It is retained as truthful coordination evidence rather than hidden or rewritten.

## Post-E2E freeze

After detecting the overlap, the Alpaca execution lane was frozen for submission finalization. The allowed work is now limited to read-only/runtime/submission operations.

Forbidden during finalization:

- new PAPER order
- position close
- order cancel/replace
- execution retry
- changing the historical USD 100,000 baseline to current equity
- exposing credentials
- live-money trading

## Final public runtime proof

After an audited `systemd --user` service reload, the public runtime reported:

- `/ready`: `ok=true`
- `paper_only=true`
- `analysis_ready=true`
- `paper_path_ready=true`
- `hackathon_ready=true`
- `paper_execution_armed=false`
- `kill_switch=true`
- local Qwen reachable and expected model available
- Alpaca credentials present server-side
- PAPER API reachable
- official Alpaca MCP `ready=true`
- MCP blockers: none
- submission evidence flags for initial USD 100k and PAPER E2E: verified

`/api/mcp/status` reported explicit read-only toolsets:

`account,assets,stock-data,options-data,news`

The `trading` MCP toolset is excluded.

`/api/submission/status` reported the only remaining runtime submission blocker as:

`demo_video_missing`

## Architecture safety statement

The official Alpaca MCP sidecar remains read-only. Broker writes are only possible through the deterministic Execution Agent / Alpaca Trading API PAPER path behind the risk engine and kill switch. No additional broker write is required for hackathon finalization.
