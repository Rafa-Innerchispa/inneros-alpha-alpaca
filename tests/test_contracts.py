from inneros_alpha_alpaca.contracts import MarketSnapshot, TradeIntent


def test_symbols_are_normalized():
    assert MarketSnapshot(symbol=" spy ").symbol == "SPY"
    assert TradeIntent(symbol=" qqq ", side="buy", qty=1).symbol == "QQQ"


def test_intent_defaults_to_paper_only():
    intent = TradeIntent(symbol="SPY", side="buy", qty=1)

    assert intent.paper_only is True
    assert intent.time_in_force == "day"
