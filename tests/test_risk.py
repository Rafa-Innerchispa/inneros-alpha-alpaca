from inneros_alpha_alpaca.config import Settings
from inneros_alpha_alpaca.contracts import MarketSnapshot, TerminalState, TradeIntent
from inneros_alpha_alpaca.risk import PaperRiskEngine


def test_risk_allows_small_paper_intent():
    settings = Settings(ALLOWED_SYMBOLS="SPY", MAX_QTY=10, MAX_NOTIONAL_USD=1000)
    intent = TradeIntent(symbol="SPY", side="buy", qty=1)
    snapshot = MarketSnapshot(symbol="SPY", last=100)

    decision = PaperRiskEngine(settings).evaluate(intent, snapshot)

    assert decision.allowed is True
    assert decision.state == TerminalState.PASS


def test_risk_blocks_live_or_oversized_intent():
    settings = Settings(ALPACA_PAPER=False, ALLOWED_SYMBOLS="SPY", MAX_QTY=1, MAX_NOTIONAL_USD=10)
    intent = TradeIntent(symbol="TSLA", side="buy", qty=2, limit_price=50)

    decision = PaperRiskEngine(settings).evaluate(intent)

    assert decision.allowed is False
    assert decision.state == TerminalState.BLOCKED
    assert any("live_trading_disabled" in reason for reason in decision.reasons)
    assert any("symbol_not_allowed" in reason for reason in decision.reasons)
    assert any("qty_above_limit" in reason for reason in decision.reasons)
    assert any("notional_above_limit" in reason for reason in decision.reasons)
