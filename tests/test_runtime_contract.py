from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_local_systemd_unit_keeps_qwen_loopback_and_paper_only():
    unit = (ROOT / "deploy/inneros-alpha.service").read_text()
    assert "ALPACA_PAPER=true" in unit
    assert "INNEROS_REASONING_URL=http://127.0.0.1:8000/v1" in unit
    assert "EnvironmentFile=-%h/.config/inneros-alpha/runtime.env" in unit
    assert "Restart=on-failure" in unit


def test_primary_systemd_unit_is_generic_and_hackathon_safe():
    unit = (ROOT / "deploy/inneros-alpha-primary.service").read_text()
    assert "WorkingDirectory=%h/projects/inneros-alpha-alpaca" in unit
    assert "ALPACA_PAPER=true" in unit
    assert "ALPACA_PAPER_TRADE=true" in unit
    assert "ALPACA_API_BASE=https://paper-api.alpaca.markets" in unit
    assert "ALPACA_TOOLSETS=account,assets,stock-data,options-data,news" in unit
    assert "ALPACA_COMPETITION_ACCOUNT_DEDICATED=true" in unit
    assert "ALPACA_COMPETITION_ACCOUNT_EMAIL=" not in unit
    assert "INNEROS_REASONING_URL=http://127.0.0.1:8000/v1" in unit
    assert "%h/projects/inneros-alpha-alpaca/.venv/bin/python" in unit
    assert "--host 127.0.0.1 --port 8088" in unit
    assert "EnvironmentFile=-%h/.config/inneros-alpha/runtime.env" in unit
    assert "Restart=on-failure" in unit


def test_runtime_env_example_has_no_credentials_and_uses_shared_mcp_names():
    env = (ROOT / "deploy/runtime.env.example").read_text()
    assert "ALPACA_API_KEY=\n" in env
    assert "ALPACA_KEY_ID=\n" in env
    assert "ALPACA_SECRET_KEY=\n" in env
    assert "ALPACA_COMPETITION_ACCOUNT_EMAIL=\n" in env
    assert "ALPACA_TOOLSETS=account,assets,stock-data,options-data,news" in env
    assert "ALPACA_COMPETITION_ACCOUNT_DEDICATED=true" in env
    assert "https://paper-api.alpaca.markets" in env
    assert "api.alpaca.markets\n" not in env.replace("paper-api.alpaca.markets", "")


def test_runtime_runbook_keeps_private_topology_out_of_public_docs():
    doc = (ROOT / "docs/RUNTIME.md").read_text()
    assert "INNEROS_REASONING_URL=http://127.0.0.1:8000/v1" in doc
    assert "kill switch remains ON" in doc
    assert "re-arms the kill switch in `finally`" in doc
    assert "Real-money endpoint: process refuses to start" in doc
    assert "deployment-specific" in doc.lower()
