from __future__ import annotations

import os
import uuid

from .alpaca_adapter import AlpacaPaperAdapter
from .models import (
    ExecutionResult,
    PipelineResult,
    RiskDecision,
    TraceEvent,
    TradeIntent,
    TruthState,
)
from .reasoning import LocalReasoningClient
from .risk import RiskEngine


class PipelineService:
    def __init__(
        self,
        adapter: AlpacaPaperAdapter | None = None,
        reasoner: LocalReasoningClient | None = None,
        risk_engine: RiskEngine | None = None,
    ) -> None:
        self.adapter = adapter or AlpacaPaperAdapter()
        self.reasoner = reasoner or LocalReasoningClient()
        self.risk_engine = risk_engine or RiskEngine()
        self.kill_switch = os.getenv("INNEROS_KILL_SWITCH_DEFAULT", "true").lower() == "true"
        self._traces: dict[str, list[TraceEvent]] = {}

    def set_kill_switch(self, enabled: bool) -> bool:
        self.kill_switch = bool(enabled)
        return self.kill_switch

    def get_trace(self, correlation_id: str) -> list[TraceEvent]:
        return list(self._traces.get(correlation_id, []))

    def _append(
        self,
        trace: list[TraceEvent],
        *,
        source: str,
        from_agent: str,
        to_agent: str,
        event: str,
        status: TruthState,
        detail: str,
        correlation_id: str,
    ) -> None:
        trace.append(
            TraceEvent(
                source=source,
                from_agent=from_agent,
                to_agent=to_agent,
                event=event,
                status=status,
                detail=detail,
                correlation_id=correlation_id,
            )
        )

    def run(self, ticker: str, execute: bool = False) -> PipelineResult:
        correlation_id = str(uuid.uuid4())
        trace: list[TraceEvent] = []

        snapshot = self.adapter.get_market_snapshot(ticker=ticker, correlation_id=correlation_id)
        market_state = TruthState.LIVE if snapshot.source == TruthState.LIVE.value else TruthState.FIXTURE
        self._append(
            trace,
            source=snapshot.source,
            from_agent="alpaca-market",
            to_agent="strategy-agent",
            event="market_snapshot",
            status=market_state,
            detail=f"{snapshot.ticker} price={snapshot.price} freshness={snapshot.freshness_seconds:.1f}s",
            correlation_id=correlation_id,
        )

        intent = self.reasoner.propose(snapshot)
        strategy_state = TruthState.NO_TRADE if intent.bias == "NEUTRAL" or intent.strategy == "no_trade" else TruthState.LIVE
        self._append(
            trace,
            source="LOCAL_QWEN",
            from_agent="strategy-agent",
            to_agent="risk-engine",
            event="trade_intent",
            status=strategy_state,
            detail=f"{intent.strategy} {intent.bias} confidence={intent.confidence:.2f}",
            correlation_id=correlation_id,
        )

        portfolio = self.adapter.get_portfolio()
        risk: RiskDecision = self.risk_engine.evaluate(
            snapshot=snapshot,
            intent=intent,
            portfolio_equity=portfolio.equity,
            open_positions=portfolio.open_positions,
            daily_pnl=portfolio.day_pl,
            kill_switch=self.kill_switch,
        )
        risk_state = {
            "PASS": TruthState.PASS,
            "NO_TRADE": TruthState.NO_TRADE,
            "BLOCKED": TruthState.BLOCKED,
        }[risk.status]
        self._append(
            trace,
            source="DETERMINISTIC",
            from_agent="risk-engine",
            to_agent="execution-agent",
            event="risk_decision",
            status=risk_state,
            detail=(risk.status if not risk.triggered_gates else f"{risk.status}: {', '.join(risk.triggered_gates)}"),
            correlation_id=correlation_id,
        )

        if not execute:
            execution = ExecutionResult(
                status="blocked",
                message="Analysis-only run; execute=false, no broker request sent",
                correlation_id=correlation_id,
            )
            execution_state = TruthState.NO_TRADE
        elif self.kill_switch:
            execution = ExecutionResult(
                status="blocked",
                message="Server kill switch is ON; no broker request sent",
                correlation_id=correlation_id,
            )
            execution_state = TruthState.BLOCKED
        else:
            execution = self.adapter.submit_order(intent, risk)
            execution_state = TruthState.PAPER_LIVE if execution.status == "submitted" else TruthState.BLOCKED

        self._append(
            trace,
            source="ALPACA_PAPER",
            from_agent="execution-agent",
            to_agent="evidence-store",
            event="execution_result",
            status=execution_state,
            detail=f"{execution.status}: {execution.message}",
            correlation_id=correlation_id,
        )

        self._traces[correlation_id] = trace
        return PipelineResult(
            correlation_id=correlation_id,
            snapshot=snapshot,
            intent=intent,
            risk=risk,
            execution=execution,
            trace=trace,
        )
