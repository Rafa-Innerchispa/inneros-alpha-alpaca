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
- [x] Local Qwen reasoning path is reachable and the expected model was verified server-side.

## Account and live-integration proof

- [x] Dedicated competition account is declared in runtime configuration.
- [x] Account identity/email presence is configured server-side without exposing it publicly.
- [x] Starting PAPER equity of USD 100,000 was verified before the first controlled PAPER submission.
- [x] PAPER API key and secret are stored server-side and validated against Alpaca PAPER with HTTP 200.
- [ ] `/api/mcp/status` returns PAPER + read-only + options-data + credentials present after final service reload.
- [ ] Alpaca MCP live account probe succeeds after final service reload.
- [ ] Alpaca MCP live options-data probe succeeds after final service reload.
- [ ] `/ready` returns `hackathon_ready=true` after final service reload.

## Controlled E2E proof

- [x] Server kill switch starts ON.
- [x] A fail-closed PAPER proof helper exists: `python -m src.controlled_paper_e2e SPY`.
- [x] The helper requires explicit `--confirm-paper-order` before any broker write is permitted.
- [x] The helper requires a PAPER_LIVE account and the verified USD 100,000 pre-trade baseline before the first controlled order.
- [x] The helper re-arms the kill switch in `finally`, including exception paths.
- [x] Market/account data was live for the controlled PAPER proof.
- [x] Qwen returned a structured TradeIntent in the controlled pipeline.
- [x] Contract Selector produced a valid options contract.
- [x] Risk Engine returned PASS for the bounded trade.
- [x] Execution Agent submitted a PAPER order through the Trading API.
- [x] Canonical Alpaca order ID was captured in evidence: `6e1cc1de-821c-49e1-8605-c8161caf1a05`.
- [x] Canonical pipeline correlation ID was captured: `8006ee08-104a-4bcc-91c7-1013ae4b1a41`.
- [x] Correlation consistency and evidence persistence were verified.
- [x] Kill switch re-arm was captured after the controlled run.
- [x] A later overlapping agent execution was detected and documented; a second PAPER order ID exists and is not treated as the canonical proof.
- [x] Alpaca execution is frozen for submission finalization: no additional order, close, cancel, replace or retry.

## Submission package

- [x] Replace stale PENDING LIVE EVIDENCE claims in `SUBMISSION_WRITEUP.md` with verified evidence only.
- [x] Mark write-up finalized in runtime readiness.
- [ ] Record judge-facing demo/video.
- [ ] Store final demo/video URL in runtime readiness.
- [x] Final README check: setup, PAPER-only guard, architecture, Alpaca MCP/Trading API, controlled E2E and tests.
- [x] Verify repository contains no credentials, competition-account identity or private deployment topology. Guarded by `tests/test_repository_hygiene.py`.
- [x] Final repository-hygiene test baseline: **55/55 PASS** before docs-only evidence updates.
- [ ] Verify final submission fields and deadline on the official event page.
- [ ] Complete LabLab submission fields from the canonical write-up.
- [ ] Submit only after final human review of claims, links and evidence.

## Final controlled PAPER command

Preflight-only command remains available for code verification:

```bash
python -m src.controlled_paper_e2e SPY
```

**Do not run the confirmed execution command again for submission finalization.** The PAPER E2E proof already exists and a concurrency incident produced a second PAPER submission before the freeze. All remaining work is read-only/runtime/submission reconciliation.
