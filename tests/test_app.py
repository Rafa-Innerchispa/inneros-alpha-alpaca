from fastapi.testclient import TestClient

from inneros_alpha_alpaca.app import app


client = TestClient(app)


def test_health_is_paper_only_without_secret_values():
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["paper_only"] is True
    assert "ALPACA_SECRET_KEY" not in str(body)


def test_evaluate_intent_blocks_unallowed_symbol():
    response = client.post(
        "/api/intents/evaluate?last_price=100",
        json={"symbol": "BTCUSD", "side": "buy", "qty": 1},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["allowed"] is False
    assert body["state"] == "BLOCKED"


def test_paper_order_without_credentials_does_not_trade():
    response = client.post(
        "/api/orders/paper?last_price=100",
        json={"symbol": "SPY", "side": "buy", "qty": 1},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "NO_TRADE"
    assert body["evidence"]["reason"] == "alpaca_paper_credentials_missing"
