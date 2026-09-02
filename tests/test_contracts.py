from datetime import date, timedelta

from src.contracts import ContractPolicy, DeterministicContractSelector
from src.models import MarketSnapshot, OptionContractCandidate, TradeIntent


TODAY = date(2026, 9, 1)


def snapshot(correlation_id: str = "corr-contract") -> MarketSnapshot:
    return MarketSnapshot(
        ticker="SPY",
        source="LIVE",
        price=500,
        freshness_seconds=1,
        correlation_id=correlation_id,
    )


def intent(correlation_id: str = "corr-contract", bias: str = "BULLISH") -> TradeIntent:
    return TradeIntent(
        ticker="SPY",
        bias=bias,
        confidence=0.8,
        strategy="long_call" if bias == "BULLISH" else "long_put",
        dte_target=30,
        rationale="test intent",
        estimated_max_loss=0,
        correlation_id=correlation_id,
    )


def candidate(
    symbol: str,
    *,
    dte: int = 30,
    option_type: str = "call",
    strike: float = 505,
    bid: float = 4.8,
    ask: float = 5.0,
    delta: float | None = 0.35,
    tradable: bool = True,
) -> OptionContractCandidate:
    return OptionContractCandidate(
        symbol=symbol,
        underlying_symbol="SPY",
        option_type=option_type,
        strike_price=strike,
        expiration_date=TODAY + timedelta(days=dte),
        tradable=tradable,
        bid_price=bid,
        ask_price=ask,
        bid_size=20,
        ask_size=20,
        delta=delta,
    )


def test_selects_liquid_contract_and_computes_long_option_max_loss():
    selector = DeterministicContractSelector()
    result = selector.select(
        snapshot=snapshot(),
        intent=intent(),
        candidates=[
            candidate("SPY_BAD_SPREAD", bid=2, ask=5),
            candidate("SPY_GOOD", bid=4.8, ask=5.0),
        ],
        today=TODAY,
    )
    assert result.status == "SELECTED"
    assert result.contract.symbol == "SPY_GOOD"
    assert result.estimated_max_loss == 500
    assert result.spread_pct < 0.15


def test_rejects_out_of_range_dte_wrong_type_and_nontradable():
    selector = DeterministicContractSelector()
    result = selector.select(
        snapshot=snapshot(),
        intent=intent(),
        candidates=[
            candidate("TOO_SOON", dte=7),
            candidate("TOO_LATE", dte=60),
            candidate("PUT", option_type="put"),
            candidate("HALTED", tradable=False),
        ],
        today=TODAY,
    )
    assert result.status == "NO_TRADE"
    assert "No tradable contract" in result.reason


def test_zero_quote_and_wide_spread_are_liquidity_failures():
    selector = DeterministicContractSelector(ContractPolicy(max_spread_pct=0.15))
    result = selector.select(
        snapshot=snapshot(),
        intent=intent(),
        candidates=[
            candidate("ZERO_BID", bid=0, ask=2),
            candidate("WIDE", bid=1, ask=2),
        ],
        today=TODAY,
    )
    assert result.status == "NO_TRADE"


def test_selector_can_operate_without_greeks_when_quote_is_valid():
    selector = DeterministicContractSelector()
    result = selector.select(
        snapshot=snapshot(),
        intent=intent(),
        candidates=[candidate("NO_GREEKS", delta=None)],
        today=TODAY,
    )
    assert result.status == "SELECTED"
    assert result.contract.delta is None


def test_delta_target_breaks_tie_when_available():
    selector = DeterministicContractSelector()
    result = selector.select(
        snapshot=snapshot(),
        intent=intent(),
        candidates=[
            candidate("DELTA_70", delta=0.70),
            candidate("DELTA_36", delta=0.36),
        ],
        today=TODAY,
    )
    assert result.contract.symbol == "DELTA_36"


def test_neutral_intent_never_selects_contract():
    neutral = TradeIntent(
        ticker="SPY",
        bias="NEUTRAL",
        confidence=0,
        strategy="no_trade",
        rationale="no signal",
        estimated_max_loss=0,
        correlation_id="neutral-corr",
    )
    result = DeterministicContractSelector().select(
        snapshot=snapshot("neutral-corr"),
        intent=neutral,
        candidates=[candidate("IGNORED")],
        today=TODAY,
    )
    assert result.status == "NO_TRADE"
    assert result.contract is None


def test_correlation_mismatch_blocks_before_selection():
    result = DeterministicContractSelector().select(
        snapshot=snapshot("snapshot-corr"),
        intent=intent("intent-corr"),
        candidates=[candidate("IGNORED")],
        today=TODAY,
    )
    assert result.status == "BLOCKED"
    assert "Correlation mismatch" in result.reason
