from datetime import date, timedelta

from src.models import ExecutionResult, MarketSnapshot, OptionContractCandidate, PortfolioView, TradeIntent, TruthState
from src.pipeline import PipelineService
from src.risk import RiskEngine


class FakeAdapter:
    configured = True

    def get_market_snapshot(self, ticker: str, correlation_id: str) -> MarketSnapshot:
        return MarketSnapshot(
            ticker=ticker,
            source="FIXTURE",
            price=500,
            freshness_seconds=1,
            correlation_id=correlation_id,
        )

    def get_option_candidates(self, **kwargs):
        return [
            OptionContractCandidate(
                symbol="SPY_TEST_CALL",
                underlying_symbol="SPY",
                option_type="call",
                strike_price=505,
                expiration_date=date.today() + timedelta(days=30),
                tradable=True,
                bid_price=4.80,
                ask_price=5.00,
                bid_size=20,
                ask_size=20,
                delta=0.36,
            )
        ]

    def get_portfolio(self) -> PortfolioView:
        return PortfolioView(
            equity=100000,
            cash=100000,
            buying_power=200000,
            open_positions=0,
            source=TruthState.FIXTURE,
        )

    def submit_order(self, intent, risk) -> ExecutionResult:
        return ExecutionResult(
            status="submitted",
            alpaca_order_id="paper-test-order",
            message="fake paper submit",
            correlation_id=intent.correlation_id,
        )


class FakeReasoner:
    model = "fake-local-qwen"
    base_url = "local://fake"

    def propose(self, snapshot: MarketSnapshot) -> TradeIntent:
        return TradeIntent(
            ticker=snapshot.ticker,
            bias="BULLISH",
            confidence=0.8,
            strategy="long_call",
            dte_target=30,
            rationale="fixture bullish signal",
            estimated_max_loss=0,
            correlation_id=snapshot.correlation_id,
        )


def service() -> PipelineService:
    instance = PipelineService(
        adapter=FakeAdapter(),
        reasoner=FakeReasoner(),
        risk_engine=RiskEngine(),
    )
    instance.kill_switch = False
    return instance


def test_pipeline_propagates_single_correlation_id_and_contract():
    result = service().run("SPY", execute=False)
    corr = result.correlation_id
    assert result.snapshot.correlation_id == corr
    assert result.intent.correlation_id == corr
    assert result.contract_selection.correlation_id == corr
    assert result.risk.correlation_id == corr
    assert result.execution.correlation_id == corr
    assert all(event.correlation_id == corr for event in result.trace)
    assert result.contract_selection.status == "SELECTED"
    assert result.intent.option_symbol == "SPY_TEST_CALL"
    assert result.intent.estimated_max_loss == 500
    assert result.risk.status == "PASS"
    assert result.execution.status == "blocked"
    assert "execute=false" in result.execution.message


def test_server_kill_switch_blocks_risk_and_execution():
    instance = service()
    instance.kill_switch = True
    result = instance.run("SPY", execute=True)
    assert result.contract_selection.status == "SELECTED"
    assert result.risk.status == "BLOCKED"
    assert "KILL_SWITCH" in result.risk.triggered_gates
    assert result.execution.status == "blocked"
    assert "kill switch" in result.execution.message.lower()
    assert any(event.status == TruthState.BLOCKED for event in result.trace)


def test_paper_execution_only_after_selection_and_risk_pass():
    instance = service()
    instance.kill_switch = False
    result = instance.run("SPY", execute=True)
    assert result.contract_selection.status == "SELECTED"
    assert result.risk.status == "PASS"
    assert result.execution.status == "submitted"
    assert result.execution.alpaca_order_id == "paper-test-order"
    assert result.trace[-1].status == TruthState.PAPER_LIVE


def test_trace_and_evidence_are_retrievable_after_pipeline_run():
    instance = service()
    result = instance.run("SPY", execute=False)
    stored = instance.get_trace(result.correlation_id)
    assert len(stored) == 5
    assert stored[0].event == "market_snapshot"
    assert stored[2].event == "contract_selection"
    assert stored[-1].event == "execution_result"
    evidence = instance.get_evidence(result.correlation_id)
    assert evidence["correlation_id"] == result.correlation_id
    assert evidence["contract_selection"]["status"] == "SELECTED"
    assert evidence["schema_version"] == "inneros.alpha.evidence.v1"
