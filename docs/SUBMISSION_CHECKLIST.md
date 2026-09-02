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
- [x] One-page write-up draft exists.

## Account and live-integration proof

- [ ] Dedicated competition account is configured in runtime.
- [ ] Account identity/email presence is configured server-side without exposing it publicly.
- [ ] Starting PAPER equity of USD 100,000 is verified and evidence captured before trading.
- [ ] New PAPER API key and secret from the competition account are stored server-side.
- [ ] `/api/mcp/status` returns PAPER + read-only + options-data + credentials present.
- [ ] Alpaca MCP live account probe succeeds.
- [ ] Alpaca MCP live options-data probe succeeds.
- [ ] `/ready` returns `hackathon_ready=true`.

## Controlled E2E proof

- [ ] Server kill switch starts ON.
- [ ] Market snapshot is live and fresh.
- [ ] Qwen returns a structured TradeIntent with the same correlation ID.
- [ ] Contract Selector produces a valid options contract or truthfully returns NO_TRADE.
- [ ] Risk Engine PASS is captured for an approved bounded trade.
- [ ] Kill switch is deliberately disarmed only for the controlled PAPER test.
- [ ] Execution Agent submits one PAPER order through the Trading API.
- [ ] Alpaca order ID is captured in evidence.
- [ ] The same correlation ID is visible from Market -> Strategy -> Contract -> Risk -> Execution -> Evidence.
- [ ] Kill switch is re-armed immediately after the controlled test.

## Submission package

- [ ] Replace all PENDING LIVE EVIDENCE markers in `SUBMISSION_WRITEUP.md` with real evidence only.
- [ ] Mark write-up finalized in runtime readiness.
- [ ] Record judge-facing demo/video.
- [ ] Store final demo URL in runtime readiness.
- [ ] Final README check: setup, PAPER-only guard, architecture, Alpaca MCP/Trading API, tests.
- [ ] Verify repository contains no credentials or private topology.
- [ ] Run complete test suite on final `main`.
- [ ] Verify final submission fields and deadline on the official event page.
- [ ] Submit only after a final human review of claims, links and evidence.
