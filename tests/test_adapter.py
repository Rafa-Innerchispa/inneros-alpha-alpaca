import pytest

from src.alpaca_adapter import AlpacaPaperAdapter
from src.models import RiskDecision, TradeIntent, TruthState


def clear_alpaca_env(monkeypatch):
    for key in (
        "ALPACA_KEY_ID",
        "ALPACA_SECRET_KEY",
        "ALPACA_API_KEY",
        "ALPACA_API_SECRET",
        "ALPACA_API_BASE",
        "ALPACA_BASE_URL",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("ALPACA_PAPER", "true")


def test_unconfigured_adapter_is_explicit_fixture(monkeypatch):
    clear_alpaca_env(monkeypatch)
    adapter = AlpacaPaperAdapter()
    portfolio = adapter.get_portfolio()
    snapshot = adapter.get_market_snapshot("SPY", "corr-1")
    assert portfolio.source == TruthState.FIXTURE
    assert snapshot.source == "FIXTURE"
    assert snapshot.correlation_id == "corr-1"


def test_live_trading_url_is_rejected(monkeypatch):
    clear_alpaca_env(monkeypatch)
    monkeypatch.setenv("ALPACA_API_BASE", "https://api.alpaca.markets")
    with pytest.raises(RuntimeError, match="Paper-only guard"):
        AlpacaPaperAdapter()


def test_execute_requires_matching_correlation_and_selected_contract(monkeypatch):
    clear_alpaca_env(monkeypatch)
    adapter = AlpacaPaperAdapter()
    intent = TradeIntent(
        ticker="SPY",
        bias="BULLISH",
        confidence=0.8,
        strategy="long_call",
        dte_target=30,
        rationale="test",
        estimated_max_loss=500,
        correlation_id="intent-corr",
    )
    wrong_risk = RiskDecision(status="PASS", correlation_id="risk-corr")
    mismatch = adapter.submit_order(intent, wrong_risk)
    assert mismatch.status == "blocked"
    assert "Correlation mismatch" in mismatch.message

    matching_risk = RiskDecision(status="PASS", correlation_id="intent-corr")
    no_credentials = adapter.submit_order(intent, matching_risk)
    assert no_credentials.status == "blocked"
    assert "credentials" in no_credentials.message.lower()
