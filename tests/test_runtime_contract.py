from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_systemd_unit_keeps_qwen_loopback_and_paper_only():
    unit = (ROOT / "deploy/inneros-alpha.service").read_text()
    assert "ALPACA_PAPER=true" in unit
    assert "INNEROS_REASONING_URL=http://127.0.0.1:8000/v1" in unit
    assert "--host 0.0.0.0 --port 8088" in unit
    assert "EnvironmentFile=-%h/.config/inneros-alpha/runtime.env" in unit
    assert "Restart=on-failure" in unit


def test_runtime_env_example_has_no_credentials():
    env = (ROOT / "deploy/runtime.env.example").read_text()
    assert "ALPACA_KEY_ID=\n" in env
    assert "ALPACA_SECRET_KEY=\n" in env
    assert "https://paper-api.alpaca.markets" in env
    assert "api.alpaca.markets\n" not in env.replace("paper-api.alpaca.markets", "")


def test_runtime_runbook_requires_kill_switch_for_paper_test():
    doc = (ROOT / "docs/RUNTIME.md").read_text()
    assert "kill switch remains ON" in doc
    assert "Re-arm immediately" in doc
    assert "Real-money endpoint: process refuses to start" in doc
