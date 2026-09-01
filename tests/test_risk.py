from src.models import MarketSnapshot, TradeIntent
from src.risk import RiskEngine


def snapshot(correlation_id: str, freshness: float = 1):
    return MarketSnapshot(
        ticker="SPY",
        source="FIXTURE",
        price=500,
        freshness_seconds=freshness,
        correlation_id=correlation_id,
    )


def intent(correlation_id: str, max_loss: float = 500, confidence: float = 0.8):
    return TradeIntent(
        ticker="SPY",
        bias="BULLISH",
        confidence=confidence,
        strategy="long_call",
        dte_target=30,
        rationale="test",
        estimated_max_loss=max_loss,
        correlation_id=correlation_id,
    )


def test_pass_when_within_limits():
    engine = RiskEngine()
    result = engine.evaluate(
        snapshot=snapshot("ok-1"),
        intent=intent("ok-1"),
        portfolio_equity=100000,
        open_positions=0,
        daily_pnl=0,
    )
    assert result.status == "PASS"


def test_blocks_oversized_trade():
    engine = RiskEngine()
    result = engine.evaluate(
        snapshot=snapshot("big-1"),
        intent=intent("big-1", max_loss=1500),
        portfolio_equity=100000,
        open_positions=0,
        daily_pnl=0,
    )
    assert result.status == "BLOCKED"
    assert "MAX_RISK_PER_TRADE" in result.triggered_gates


def test_blocks_stale_data():
    engine = RiskEngine()
    result = engine.evaluate(
        snapshot=snapshot("stale-1", freshness=60),
        intent=intent("stale-1"),
        portfolio_equity=100000,
        open_positions=0,
        daily_pnl=0,
    )
    assert result.status == "BLOCKED"
    assert "STALE_MARKET_DATA" in result.triggered_gates


def test_kill_switch_blocks():
    engine = RiskEngine()
    result = engine.evaluate(
        snapshot=snapshot("kill-1"),
        intent=intent("kill-1"),
        portfolio_equity=100000,
        open_positions=0,
        daily_pnl=0,
        kill_switch=True,
    )
    assert result.status == "BLOCKED"
    assert "KILL_SWITCH" in result.triggered_gates
