from __future__ import annotations

import os
import uuid

from .alpaca_adapter import AlpacaPaperAdapter
from .contracts import DeterministicContractSelector
from .evidence import EvidenceStore
from .models import (
    ContractSelection,
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
        contract_selector: DeterministicContractSelector | None = None,
        evidence_store: EvidenceStore | None = None,
    ) -> None:
        self.adapter = adapter or AlpacaPaperAdapter()
        self.reasoner = reasoner or LocalReasoningClient()
        self.risk_engine = risk_engine or RiskEngine()
        self.contract_selector = contract_selector or DeterministicContractSelector()
        self.evidence = evidence_store or EvidenceStore()
        self.kill_switch = os.getenv("INNEROS_KILL_SWITCH_DEFAULT", "true").lower() == "true"
        self._traces: dict[str, list[TraceEvent]] = {}

    def set_kill_switch(self, enabled: bool) -> bool:
        self.kill_switch = bool(enabled)
        return self.kill_switch

    def get_trace(self, correlation_id: str) -> list[TraceEvent]:
        cached = self._traces.get(correlation_id)
        if cached is not None:
            return list(cached)
        evidence = self.evidence.get(correlation_id)
        if not evidence:
            return []
        return [TraceEvent.model_validate(event) for event in evidence.get("trace", [])]

    def get_evidence(self, correlation_id: str):
        return self.evidence.get(correlation_id)

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

    def _select_contract(self, snapshot, intent: TradeIntent) -> tuple[TradeIntent, ContractSelection]:
        if intent.bias == "NEUTRAL" or intent.strategy == "no_trade":
            selection = self.contract_selector.select(snapshot=snapshot, intent=intent, candidates=[])
            return intent, selection

        option_type = "call" if intent.bias == "BULLISH" else "put"
        candidates = self.adapter.get_option_candidates(
            ticker=snapshot.ticker,
            option_type=option_type,
            underlying_price=snapshot.price,
            min_dte=self.contract_selector.policy.min_dte,
            max_dte=self.contract_selector.policy.max_dte,
        )
        selection = self.contract_selector.select(
            snapshot=snapshot,
            intent=intent,
            candidates=candidates,
        )
        if selection.status == "SELECTED":
            return self.contract_selector.apply_to_intent(intent, selection), selection

        no_trade = intent.model_copy(deep=True)
        no_trade.bias = "NEUTRAL"
        no_trade.strategy = "no_trade"
        no_trade.confidence = 0
        no_trade.option_symbol = None
        no_trade.estimated_max_loss = 0
        no_trade.rationale = f"{intent.rationale} | Contract gate: {selection.reason}"
        return no_trade, selection

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
            to_agent="contract-selector",
            event="trade_intent",
            status=strategy_state,
            detail=f"{intent.strategy} {intent.bias} confidence={intent.confidence:.2f}",
            correlation_id=correlation_id,
        )

        intent, selection = self._select_contract(snapshot, intent)
        contract_state = {
            "SELECTED": TruthState.PASS,
            "NO_TRADE": TruthState.NO_TRADE,
            "BLOCKED": TruthState.BLOCKED,
        }[selection.status]
        contract_detail = selection.reason
        if selection.contract is not None:
            contract_detail = (
                f"{selection.contract.symbol} strike={selection.contract.strike_price} "
                f"expiry={selection.contract.expiration_date.isoformat()} "
                f"spread={selection.spread_pct:.3f} max_loss={selection.estimated_max_loss:.2f}"
            )
        self._append(
            trace,
            source="DETERMINISTIC",
            from_agent="contract-selector",
            to_agent="risk-engine",
            event="contract_selection",
            status=contract_state,
            detail=contract_detail,
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

        result = PipelineResult(
            correlation_id=correlation_id,
            snapshot=snapshot,
            intent=intent,
            contract_selection=selection,
            risk=risk,
            execution=execution,
            trace=trace,
        )
        self._traces[correlation_id] = trace
        self.evidence.persist(result)
        return result
