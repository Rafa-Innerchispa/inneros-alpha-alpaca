from src.mcp_readiness import READ_ONLY_TOOLSETS, alpaca_mcp_readiness, recommended_mcp_env


def _ready_env() -> dict[str, str]:
    return {
        "ALPACA_API_KEY": "paper-key-fixture",
        "ALPACA_SECRET_KEY": "paper-secret-fixture",
        "ALPACA_PAPER_TRADE": "true",
        "ALPACA_TOOLSETS": ",".join(READ_ONLY_TOOLSETS),
    }


def test_missing_explicit_toolsets_fails_closed() -> None:
    state = alpaca_mcp_readiness(
        {
            "ALPACA_API_KEY": "paper-key-fixture",
            "ALPACA_SECRET_KEY": "paper-secret-fixture",
            "ALPACA_PAPER_TRADE": "true",
        }
    )
    assert state.ready is False
    assert state.read_only is False
    assert "mcp_toolsets_must_be_explicit" in state.blockers


def test_recommended_read_only_mcp_config_is_ready() -> None:
    state = alpaca_mcp_readiness(_ready_env())
    assert state.ready is True
    assert state.paper_trade is True
    assert state.read_only is True
    assert "options-data" in state.toolsets
    assert "trading" not in state.toolsets
    assert state.command == ("uvx", "alpaca-mcp-server")


def test_trading_toolset_is_forbidden_for_agent_sidecar() -> None:
    env = _ready_env()
    env["ALPACA_TOOLSETS"] += ",trading"
    state = alpaca_mcp_readiness(env)
    assert state.ready is False
    assert state.read_only is False
    assert "mcp_write_toolsets_forbidden:trading" in state.blockers


def test_live_mcp_is_forbidden() -> None:
    env = _ready_env()
    env["ALPACA_PAPER_TRADE"] = "false"
    state = alpaca_mcp_readiness(env)
    assert state.ready is False
    assert "mcp_live_trading_forbidden" in state.blockers


def test_missing_credentials_are_reported_without_values() -> None:
    env = recommended_mcp_env()
    state = alpaca_mcp_readiness(env)
    public = state.public_dict()
    assert state.ready is False
    assert "alpaca_api_key_missing" in state.blockers
    assert "alpaca_secret_key_missing" in state.blockers
    assert "paper-key-fixture" not in repr(public)
    assert "paper-secret-fixture" not in repr(public)
    assert set(public) == {
        "paper_trade",
        "explicit_toolsets",
        "toolsets",
        "read_only",
        "api_key_present",
        "secret_key_present",
        "command",
        "ready",
        "blockers",
    }
