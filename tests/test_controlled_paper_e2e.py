from __future__ import annotations

from types import SimpleNamespace

from src.controlled_paper_e2e import controlled_paper_e2e
from src.models import (
    ContractSelection,
    ExecutionResult,
    MarketSnapshot,
    OptionContractCandidate,
    PipelineResult,
    PortfolioView,
    RiskDecision,
    TraceEvent,
    TradeIntent,
    TruthState,
)


class FakeAdapter:
    def __init__(self, configured: bool = True, equity: float = 100000.0):
        self.configured = configured
        self._equity = equity

    def get_portfolio(self):
        return PortfolioView(
            equity=self._equity,
            cash=self._equity,
            buying_power=self._equity * 2,
            open_positions=0,
            paper=True,
            source=TruthState.PAPER_LIVE,
        )


class FakeReasoner:
    def status(self):
        return {"reachable": True, "model_available": True, "model": "fixture-qwen"}


class FakeService:
    def __init__(self, *, configured: bool = True, equity: float = 100000.0, raise_on_run: bool = False):
        self.adapter = FakeAdapter(configured=configured, equity=equity)
        self.reasoner = FakeReasoner()
        self.kill_switch = True
        self.raise_on_run = raise_on_run
        self.evidence = SimpleNamespace(backend="memory")
        self._evidence = {}

    def set_kill_switch(self, enabled: bool):
        self.kill_switch = bool(enabled)
        return self.kill_switch

    def run(self, ticker: str, execute: bool = False):
        assert execute is True
        assert self.kill_switch is False
        if self.raise_on_run:
            raise RuntimeError("fixture broker failure")
        cid = "corr-paper-1"
        contract = OptionContractCandidate(
            symbol="SPY260918C00500000",
            underlying_symbol="SPY",
            option_type="call",
            strike_price=500,
            expiration_date="2026-09-18",
            tradable=True,
            bid_price=2.0,
            ask_price=2.1,
            bid_size=20,
            ask_size=20,
            delta=0.5,
        )
        result = PipelineResult(
            correlation_id=cid,
            snapshot=MarketSnapshot(ticker=ticker, source="LIVE", price=500, correlation_id=cid),
            intent=TradeIntent(
                ticker=ticker,
                bias="BULLISH",
                confidence=0.8,
                strategy="long_call",
                rationale="fixture",
                estimated_max_loss=210,
                option_symbol=contract.symbol,
                correlation_id=cid,
            ),
            contract_selection=ContractSelection(
                status="SELECTED",
                contract=contract,
                reason="fixture selected",
                estimated_max_loss=210,
                spread_pct=0.05,
                correlation_id=cid,
            ),
            risk=RiskDecision(status="PASS", max_loss=210, portfolio_risk_pct=0.0021, correlation_id=cid),
            execution=ExecutionResult(
                status="submitted",
                alpaca_order_id="paper-order-1",
                message="Submitted to Alpaca PAPER endpoint",
                correlation_id=cid,
            ),
            trace=[
                TraceEvent(
                    source="ALPACA_PAPER",
                    from_agent="execution-agent",
                    to_agent="evidence-store",
                    event="execution_result",
                    status=TruthState.PAPER_LIVE,
                    detail="submitted",
                    correlation_id=cid,
                )
            ],
        )
        self._evidence[cid] = result.model_dump(mode="json")
        return result

    def get_evidence(self, correlation_id: str):
        return self._evidence.get(correlation_id)


def test_missing_credentials_fail_closed_without_disarming_kill_switch():
    service = FakeService(configured=False)
    report = controlled_paper_e2e(service=service, confirm_paper_order=True)
    assert report["ok"] is False
    assert report["blocker"] == "alpaca_paper_credentials_missing"
    assert service.kill_switch is True


def test_equity_must_be_100k_before_first_controlled_order():
    service = FakeService(equity=99999.0)
    report = controlled_paper_e2e(service=service, confirm_paper_order=True)
    assert report["ok"] is False
    assert report["blocker"] == "competition_initial_100k_not_verified"
    assert service.kill_switch is True


def test_preflight_never_submits_order_without_explicit_confirmation():
    service = FakeService()
    report = controlled_paper_e2e(service=service, confirm_paper_order=False)
    assert report["ok"] is True
    assert report["status"] == "READY_FOR_CONTROLLED_PAPER_ORDER"
    assert report["order_submitted"] is False
    assert service.kill_switch is True


def test_controlled_paper_order_captures_order_and_rearms_kill_switch():
    service = FakeService()
    report = controlled_paper_e2e(service=service, confirm_paper_order=True)
    assert report["ok"] is True
    assert report["status"] == "PAPER_LIVE"
    assert report["alpaca_order_id"] == "paper-order-1"
    assert report["correlation_id"] == "corr-paper-1"
    assert report["correlation_consistent"] is True
    assert report["evidence_persisted"] is True
    assert report["kill_switch_rearmed"] is True
    assert service.kill_switch is True


def test_kill_switch_rearms_even_when_pipeline_raises():
    service = FakeService(raise_on_run=True)
    report = controlled_paper_e2e(service=service, confirm_paper_order=True)
    assert report["ok"] is False
    assert report["blocker"] == "controlled_pipeline_exception"
    assert report["kill_switch_rearmed"] is True
    assert service.kill_switch is True
