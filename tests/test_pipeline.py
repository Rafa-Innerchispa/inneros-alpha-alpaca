from src.models import ExecutionResult, MarketSnapshot, PortfolioView, TradeIntent, TruthState
from src.pipeline import PipelineService
from src.risk import RiskEngine


class FakeAdapter:
    configured = False

    def get_market_snapshot(self, ticker: str, correlation_id: str) -> MarketSnapshot:
        return MarketSnapshot(
            ticker=ticker,
            source="FIXTURE",
            price=500,
            freshness_seconds=1,
            correlation_id=correlation_id,
        )

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
            status="blocked",
            message="fake adapter never submits",
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
            estimated_max_loss=500,
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


def test_pipeline_propagates_single_correlation_id():
    result = service().run("SPY", execute=False)
    corr = result.correlation_id
    assert result.snapshot.correlation_id == corr
    assert result.intent.correlation_id == corr
    assert result.risk.correlation_id == corr
    assert result.execution.correlation_id == corr
    assert all(event.correlation_id == corr for event in result.trace)
    assert result.risk.status == "PASS"
    assert result.execution.status == "blocked"
    assert "execute=false" in result.execution.message


def test_server_kill_switch_blocks_risk_and_execution():
    instance = service()
    instance.kill_switch = True
    result = instance.run("SPY", execute=True)
    assert result.risk.status == "BLOCKED"
    assert "KILL_SWITCH" in result.risk.triggered_gates
    assert result.execution.status == "blocked"
    assert "kill switch" in result.execution.message.lower()
    assert any(event.status == TruthState.BLOCKED for event in result.trace)


def test_trace_and_evidence_are_retrievable_after_pipeline_run():
    instance = service()
    result = instance.run("SPY", execute=False)
    stored = instance.get_trace(result.correlation_id)
    assert len(stored) == 4
    assert stored[0].event == "market_snapshot"
    assert stored[-1].event == "execution_result"
    evidence = instance.get_evidence(result.correlation_id)
    assert evidence["correlation_id"] == result.correlation_id
    assert evidence["schema_version"] == "inneros.alpha.evidence.v1"
