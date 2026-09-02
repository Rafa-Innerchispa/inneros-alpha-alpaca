from fastapi.testclient import TestClient

import src.main as main
from src.models import MarketSnapshot, TradeIntent


class FakeReasoner:
    model = "fake-local-qwen"
    base_url = "local://fake"

    def status(self):
        return {
            "provider": "local-amd-5",
            "runtime": "vllm",
            "model": self.model,
            "reachable": True,
            "model_available": True,
        }

    def propose(self, snapshot: MarketSnapshot) -> TradeIntent:
        return TradeIntent(
            ticker=snapshot.ticker,
            bias="BULLISH",
            confidence=0.8,
            strategy="long_call",
            dte_target=30,
            rationale="api contract test",
            estimated_max_loss=500,
            correlation_id=snapshot.correlation_id,
        )


def client() -> TestClient:
    main.pipeline.reasoner = FakeReasoner()
    main.pipeline.kill_switch = True
    return TestClient(main.app)


def test_health_and_portfolio_are_paper_only():
    api = client()
    health = api.get("/health")
    assert health.status_code == 200
    assert health.json()["paper_only"] is True
    assert health.json()["reasoning_provider"] == "local-amd-5"
    portfolio = api.get("/api/portfolio")
    assert portfolio.status_code == 200
    assert portfolio.json()["paper"] is True


def test_ready_distinguishes_analysis_from_paper_execution():
    api = client()
    ready = api.get("/ready")
    assert ready.status_code == 200
    data = ready.json()
    assert data["analysis_ready"] is True
    assert data["paper_path_ready"] is False
    assert data["paper_execution_armed"] is False
    assert data["alpaca"]["credentials_present"] is False
    assert data["console"]["path"] == "/console/"


def test_single_service_serves_console():
    api = client()
    redirect = api.get("/", follow_redirects=False)
    assert redirect.status_code == 307
    assert redirect.headers["location"] == "/console/"
    console = api.get("/console/")
    assert console.status_code == 200
    assert "Sovereign paper-trading control plane" in console.text
    js = api.get("/console/console.js")
    assert js.status_code == 200
    assert 'window.location.pathname.startsWith("/console")' in js.text


def test_server_kill_switch_round_trip():
    api = client()
    assert api.get("/api/kill-switch").json()["enabled"] is True
    changed = api.post("/api/kill-switch", json={"enabled": False})
    assert changed.status_code == 200
    assert changed.json()["enabled"] is False


def test_pipeline_contract_has_one_correlation_id_and_fails_closed_without_contracts():
    api = client()
    api.post("/api/kill-switch", json={"enabled": False})
    response = api.post("/api/pipeline/SPY?execute=false")
    assert response.status_code == 200
    data = response.json()
    corr = data["correlation_id"]
    assert data["snapshot"]["correlation_id"] == corr
    assert data["intent"]["correlation_id"] == corr
    assert data["contract_selection"]["correlation_id"] == corr
    assert data["risk"]["correlation_id"] == corr
    assert data["execution"]["correlation_id"] == corr
    assert all(event["correlation_id"] == corr for event in data["trace"])
    assert data["contract_selection"]["status"] == "NO_TRADE"
    assert data["risk"]["status"] == "NO_TRADE"
    assert data["execution"]["status"] == "blocked"
    assert len(data["trace"]) == 5
