# Alpaca hackathon final checklist

Truth rule: do not mark an item complete without evidence.

## Mandatory platform requirements

- [x] Public project repository exists: `Rafa-Innerchispa/inneros-alpha-alpaca`.
- [x] Alpaca Trading API integration is PAPER-only and rejects non-paper endpoints.
- [x] Official Alpaca MCP V2 integration is present.
- [x] MCP sidecar uses explicit read-only toolsets and excludes `trading`.
- [x] Every executable strategy uses options through the deterministic Contract Selector.
- [x] Deterministic risk gates exist and the LLM cannot override them.
- [x] Dedicated competition-account requirement is documented.
- [x] One-page write-up exists.
- [x] Public judge console is live at `https://alpaca.creatorcore.ai/console/`.
- [x] `/ready` reports `code_ready=true` and local Qwen reachable on the AMD runtime.

## Account and live-integration proof

- [x] Dedicated competition account is declared in runtime configuration.
- [x] Account identity/email presence is configured server-side without exposing it publicly.
- [ ] Starting PAPER equity of USD 100,000 is verified and evidence captured before trading.
- [ ] New PAPER API key and secret from the competition account are stored server-side.
- [ ] `/api/mcp/status` returns PAPER + read-only + options-data + credentials present.
- [ ] Alpaca MCP live account probe succeeds.
- [ ] Alpaca MCP live options-data probe succeeds.
- [ ] `/ready` returns `hackathon_ready=true`.

## Controlled E2E proof

- [x] Server kill switch starts ON in the public runtime.
- [x] A fail-closed one-command PAPER proof helper exists: `python -m src.controlled_paper_e2e SPY`.
- [x] The helper requires explicit `--confirm-paper-order` before any broker write is permitted.
- [x] The helper requires the competition account to report PAPER_LIVE and USD 100,000 equity before the first controlled order.
- [x] The helper re-arms the kill switch in `finally`, including exception paths.
- [ ] Market snapshot is live and fresh with competition credentials.
- [ ] Qwen returns a structured TradeIntent with the same correlation ID as the controlled PAPER run.
- [ ] Contract Selector produces a valid options contract or truthfully returns NO_TRADE.
- [ ] Risk Engine PASS is captured for an approved bounded trade.
- [ ] Execution Agent submits one PAPER order through the Trading API.
- [ ] Alpaca order ID is captured in evidence.
- [ ] The same correlation ID is visible from Market -> Strategy -> Contract -> Risk -> Execution -> Evidence.
- [ ] Kill switch re-arm is captured in the live E2E report.

## Submission package

- [ ] Replace all PENDING LIVE EVIDENCE markers in `SUBMISSION_WRITEUP.md` with real evidence only.
- [x] Mark write-up finalized in runtime readiness.
- [ ] Record judge-facing demo/video.
- [ ] Store final demo/video URL in runtime readiness.
- [ ] Final README check: setup, PAPER-only guard, architecture, Alpaca MCP/Trading API, tests.
- [ ] Verify repository contains no credentials or private topology.
- [ ] Run complete test suite on final branch/main.
- [ ] Verify final submission fields and deadline on the official event page.
- [ ] Submit only after a final human review of claims, links and evidence.

## Final controlled PAPER command

Preflight only, never submits an order:

```bash
python -m src.controlled_paper_e2e SPY
```

Exactly one controlled PAPER pipeline execution, only after credentials and the USD 100,000 account probe are valid:

```bash
python -m src.controlled_paper_e2e SPY --confirm-paper-order
```

The command reports the Alpaca order ID, pipeline `correlation_id`, correlation consistency, evidence persistence and kill-switch re-arm state. It does not claim a fill or P&L that Alpaca has not returned.
