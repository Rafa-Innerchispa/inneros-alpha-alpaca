from pathlib import Path

from fastapi.testclient import TestClient

from src.main import app
from src.submission_readiness import submission_readiness


def _complete_env() -> dict[str, str]:
    return {
        "ALPACA_PAPER": "true",
        "ALPACA_PAPER_TRADE": "true",
        "ALPACA_API_KEY": "paper-key-fixture",
        "ALPACA_SECRET_KEY": "paper-secret-fixture",
        "ALPACA_TOOLSETS": "account,assets,stock-data,options-data,news",
        "ALPACA_COMPETITION_ACCOUNT_EMAIL": "competition@example.test",
        "ALPACA_COMPETITION_ACCOUNT_DEDICATED": "true",
        "ALPACA_COMPETITION_INITIAL_BALANCE_VERIFIED": "true",
        "ALPACA_PAPER_E2E_VERIFIED": "true",
        "INNEROS_ALPHA_WRITEUP_FINALIZED": "true",
        "INNEROS_ALPHA_DEMO_VIDEO_URL": "https://example.test/demo",
    }


def test_code_ready_does_not_fake_submission_ready_without_live_evidence(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "SUBMISSION_WRITEUP.md").write_text("truthful draft", encoding="utf-8")
    env = {
        "ALPACA_PAPER": "true",
        "ALPACA_PAPER_TRADE": "true",
        "ALPACA_TOOLSETS": "account,assets,stock-data,options-data,news",
    }
    state = submission_readiness(env, repo_root=tmp_path)
    assert state.code_ready is True
    assert state.submission_ready is False
    assert "paper_api_credentials_missing" in state.blockers
    assert "controlled_paper_e2e_not_verified" in state.blockers
    assert "demo_video_missing" in state.blockers


def test_complete_evidence_can_be_submission_ready(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "SUBMISSION_WRITEUP.md").write_text("final truthful write-up", encoding="utf-8")
    state = submission_readiness(_complete_env(), repo_root=tmp_path)
    assert state.code_ready is True
    assert state.submission_ready is True
    assert state.blockers == ()


def test_public_readiness_never_emits_email_or_secret_values(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "SUBMISSION_WRITEUP.md").write_text("final", encoding="utf-8")
    env = _complete_env()
    public = submission_readiness(env, repo_root=tmp_path).public_dict()
    rendered = repr(public)
    assert "competition@example.test" not in rendered
    assert "paper-key-fixture" not in rendered
    assert "paper-secret-fixture" not in rendered
    assert public["competition_account_email_present"] is True
    assert public["paper_api_credentials_present"] is True


def test_legacy_trading_api_key_alias_does_not_make_mcp_live_ready(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "SUBMISSION_WRITEUP.md").write_text("draft", encoding="utf-8")
    env = _complete_env()
    env.pop("ALPACA_API_KEY")
    env["ALPACA_KEY_ID"] = "legacy-paper-key"
    state = submission_readiness(env, repo_root=tmp_path)
    assert state.paper_api_credentials_present is True
    assert state.mcp_live_ready is False
    assert "alpaca_mcp_live_not_ready" in state.blockers


def test_submission_status_endpoint_is_redacted(monkeypatch) -> None:
    for key, value in _complete_env().items():
        monkeypatch.setenv(key, value)
    client = TestClient(app)
    response = client.get("/api/submission/status")
    assert response.status_code == 200
    payload = response.json()
    assert "competition_account_email" not in payload
    assert payload["competition_account_email_present"] is True
    assert payload["paper_api_credentials_present"] is True
