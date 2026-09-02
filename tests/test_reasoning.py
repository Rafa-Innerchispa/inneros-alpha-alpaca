import httpx

from src.models import MarketSnapshot
from src.reasoning import LocalReasoningClient


def test_extract_json_accepts_fenced_payload():
    payload = LocalReasoningClient._extract_json('```json\n{"bias":"NEUTRAL"}\n```')
    assert payload["bias"] == "NEUTRAL"


def test_reasoner_fails_closed_to_no_trade(monkeypatch):
    class BrokenClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, *args, **kwargs):
            raise httpx.ConnectError("offline")

    monkeypatch.setattr(httpx, "Client", BrokenClient)
    client = LocalReasoningClient()
    snapshot = MarketSnapshot(
        ticker="SPY",
        source="FIXTURE",
        price=500,
        freshness_seconds=1,
        correlation_id="corr-fail-closed",
    )
    intent = client.propose(snapshot)
    assert intent.bias == "NEUTRAL"
    assert intent.strategy == "no_trade"
    assert intent.confidence == 0
    assert intent.estimated_max_loss == 0
    assert intent.correlation_id == snapshot.correlation_id
