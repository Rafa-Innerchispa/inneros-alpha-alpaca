from datetime import date

import httpx
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
    assert adapter.get_option_candidates(
        ticker="SPY",
        option_type="call",
        underlying_price=500,
        today=date(2026, 9, 1),
    ) == []


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


def test_option_candidates_combine_contract_metadata_quotes_and_greeks(monkeypatch):
    clear_alpaca_env(monkeypatch)
    monkeypatch.setenv("ALPACA_KEY_ID", "paper-key")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "paper-secret")

    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url, **kwargs):
            if url.endswith("/v2/options/contracts"):
                return FakeResponse(
                    {
                        "option_contracts": [
                            {
                                "symbol": "SPY261001C00505000",
                                "underlying_symbol": "SPY",
                                "type": "call",
                                "strike_price": "505",
                                "expiration_date": "2026-10-01",
                                "status": "active",
                                "tradable": True,
                            }
                        ]
                    }
                )
            if "/v1beta1/options/snapshots/SPY" in url:
                return FakeResponse(
                    {
                        "snapshots": {
                            "SPY261001C00505000": {
                                "latestQuote": {"bp": 4.8, "ap": 5.0, "bs": 12, "as": 18},
                                "greeks": {"delta": 0.36},
                            }
                        }
                    }
                )
            raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(httpx, "Client", FakeClient)
    adapter = AlpacaPaperAdapter()
    candidates = adapter.get_option_candidates(
        ticker="SPY",
        option_type="call",
        underlying_price=500,
        today=date(2026, 9, 1),
    )
    assert len(candidates) == 1
    contract = candidates[0]
    assert contract.symbol == "SPY261001C00505000"
    assert contract.bid_price == 4.8
    assert contract.ask_price == 5.0
    assert contract.bid_size == 12
    assert contract.ask_size == 18
    assert contract.delta == 0.36
