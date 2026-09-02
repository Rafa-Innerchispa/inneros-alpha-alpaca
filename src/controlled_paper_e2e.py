from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from typing import Any

from .models import PipelineResult, TruthState
from .pipeline import PipelineService

EXPECTED_STARTING_EQUITY = 100000.0
EQUITY_TOLERANCE = 0.01


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _correlation_consistent(result: PipelineResult) -> bool:
    correlation_id = result.correlation_id
    values = [
        result.snapshot.correlation_id,
        result.intent.correlation_id,
        result.risk.correlation_id,
        result.execution.correlation_id,
    ]
    if result.contract_selection is not None:
        values.append(result.contract_selection.correlation_id)
    values.extend(event.correlation_id for event in result.trace)
    return bool(correlation_id) and all(value == correlation_id for value in values)


def controlled_paper_e2e(
    ticker: str = "SPY",
    *,
    confirm_paper_order: bool = False,
    expected_starting_equity: float = EXPECTED_STARTING_EQUITY,
    service: PipelineService | None = None,
) -> dict[str, Any]:
    """Run the judge-facing PAPER proof with a fail-closed kill-switch lifecycle.

    This helper never targets live trading. Without ``confirm_paper_order`` it is
    preflight-only. With confirmation it permits one PipelineService execution,
    then re-arms the server kill switch in ``finally`` even if the broker call
    or any upstream stage raises.
    """
    pipeline = service or PipelineService()
    ticker = ticker.upper().strip() or "SPY"
    report: dict[str, Any] = {
        "ok": False,
        "paper_only": True,
        "ticker": ticker,
        "started_at": _now(),
        "confirmed": bool(confirm_paper_order),
        "expected_starting_equity": float(expected_starting_equity),
        "kill_switch_started_on": bool(pipeline.kill_switch),
        "kill_switch_rearmed": False,
        "order_submitted": False,
        "alpaca_order_id": None,
        "correlation_id": None,
    }

    if not pipeline.kill_switch:
        report.update(status="BLOCKED", blocker="kill_switch_must_start_on")
        return report

    if not pipeline.adapter.configured:
        report.update(status="BLOCKED", blocker="alpaca_paper_credentials_missing")
        return report

    reasoning = pipeline.reasoner.status()
    report["reasoning"] = {
        "reachable": bool(reasoning.get("reachable")),
        "model_available": bool(reasoning.get("model_available")),
        "model": reasoning.get("model"),
    }
    if not report["reasoning"]["reachable"] or not report["reasoning"]["model_available"]:
        report.update(status="BLOCKED", blocker="local_reasoning_not_ready")
        return report

    try:
        portfolio = pipeline.adapter.get_portfolio()
    except Exception as exc:  # network/API failure must not masquerade as readiness
        report.update(status="FAIL", blocker="alpaca_account_probe_failed", error=type(exc).__name__)
        return report

    report["account"] = {
        "source": portfolio.source.value if isinstance(portfolio.source, TruthState) else str(portfolio.source),
        "paper": bool(portfolio.paper),
        "equity": float(portfolio.equity),
        "cash": float(portfolio.cash),
        "buying_power": float(portfolio.buying_power),
        "open_positions": int(portfolio.open_positions),
    }
    if portfolio.source != TruthState.PAPER_LIVE or not portfolio.paper:
        report.update(status="BLOCKED", blocker="alpaca_account_not_paper_live")
        return report

    equity_verified = abs(float(portfolio.equity) - float(expected_starting_equity)) <= EQUITY_TOLERANCE
    report["competition_initial_100k_verified"] = equity_verified
    if not equity_verified:
        report.update(status="BLOCKED", blocker="competition_initial_100k_not_verified")
        return report

    if not confirm_paper_order:
        report.update(
            ok=True,
            status="READY_FOR_CONTROLLED_PAPER_ORDER",
            blocker=None,
            note="Preflight only. Re-run with --confirm-paper-order to permit one PAPER pipeline execution.",
        )
        return report

    result: PipelineResult | None = None
    execution_error: str | None = None
    try:
        pipeline.set_kill_switch(False)
        result = pipeline.run(ticker=ticker, execute=True)
    except Exception as exc:  # kill switch is still re-armed in finally
        execution_error = type(exc).__name__
    finally:
        report["kill_switch_rearmed"] = bool(pipeline.set_kill_switch(True))

    if result is None:
        report.update(status="FAIL", blocker="controlled_pipeline_exception", error=execution_error)
        return report

    evidence = pipeline.get_evidence(result.correlation_id)
    selection = result.contract_selection
    correlation_ok = _correlation_consistent(result)
    submitted = result.execution.status == "submitted" and bool(result.execution.alpaca_order_id)
    report.update(
        correlation_id=result.correlation_id,
        market_source=result.snapshot.source,
        strategy=result.intent.strategy,
        bias=result.intent.bias,
        contract_status=selection.status if selection is not None else None,
        option_symbol=result.intent.option_symbol,
        risk_status=result.risk.status,
        execution_status=result.execution.status,
        alpaca_order_id=result.execution.alpaca_order_id,
        order_submitted=submitted,
        correlation_consistent=correlation_ok,
        evidence_persisted=bool(evidence),
        evidence_backend=pipeline.evidence.backend,
    )

    success = bool(
        report["kill_switch_rearmed"]
        and result.snapshot.source == TruthState.LIVE.value
        and selection is not None
        and selection.status == "SELECTED"
        and result.risk.status == "PASS"
        and submitted
        and correlation_ok
        and evidence
    )
    report["ok"] = success
    report["status"] = "PAPER_LIVE" if success else "BLOCKED"
    if not success:
        report["blocker"] = "controlled_paper_e2e_incomplete"
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="InnerOS Alpha controlled Alpaca PAPER E2E proof")
    parser.add_argument("ticker", nargs="?", default="SPY")
    parser.add_argument("--confirm-paper-order", action="store_true")
    parser.add_argument("--expected-starting-equity", type=float, default=EXPECTED_STARTING_EQUITY)
    args = parser.parse_args()
    report = controlled_paper_e2e(
        args.ticker,
        confirm_paper_order=args.confirm_paper_order,
        expected_starting_equity=args.expected_starting_equity,
    )
    print(json.dumps(report, indent=2, sort_keys=True, default=str))
    return 0 if report.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
