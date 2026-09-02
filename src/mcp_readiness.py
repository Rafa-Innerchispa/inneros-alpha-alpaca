"""Alpaca MCP V2 readiness and safety contract.

The hackathon requires Alpaca's Trading API plus either the official MCP server
or CLI. InnerOS Alpha uses the official MCP server as a read-only research and
account sidecar, while all PAPER order writes remain behind the deterministic
Execution Agent and Risk Engine.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import os
from typing import Mapping

OFFICIAL_MCP_COMMAND = ("uvx", "alpaca-mcp-server")
READ_ONLY_TOOLSETS = ("account", "assets", "stock-data", "options-data", "news")
FORBIDDEN_AGENT_TOOLSETS = frozenset({"trading", "watchlists"})


def _env_bool(value: str | None, *, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_toolsets(raw: str | None) -> tuple[str, ...]:
    if raw is None:
        return ()
    return tuple(sorted({part.strip() for part in raw.split(",") if part.strip()}))


@dataclass(frozen=True)
class AlpacaMcpReadiness:
    paper_trade: bool
    explicit_toolsets: bool
    toolsets: tuple[str, ...]
    read_only: bool
    api_key_present: bool
    secret_key_present: bool
    command: tuple[str, ...]
    ready: bool
    blockers: tuple[str, ...]

    def public_dict(self) -> dict[str, object]:
        """Return a redacted payload safe for health/readiness APIs."""
        payload = asdict(self)
        payload["command"] = list(self.command)
        payload["toolsets"] = list(self.toolsets)
        payload["blockers"] = list(self.blockers)
        return payload


def alpaca_mcp_readiness(env: Mapping[str, str] | None = None) -> AlpacaMcpReadiness:
    values: Mapping[str, str] = os.environ if env is None else env
    paper_trade = _env_bool(values.get("ALPACA_PAPER_TRADE"), default=True)
    raw_toolsets = values.get("ALPACA_TOOLSETS")
    toolsets = _parse_toolsets(raw_toolsets)
    explicit_toolsets = bool(toolsets)
    forbidden = sorted(set(toolsets) & FORBIDDEN_AGENT_TOOLSETS)
    api_key_present = bool((values.get("ALPACA_API_KEY") or "").strip())
    secret_key_present = bool((values.get("ALPACA_SECRET_KEY") or "").strip())

    blockers: list[str] = []
    if not paper_trade:
        blockers.append("mcp_live_trading_forbidden")
    # Alpaca MCP defaults ALPACA_TOOLSETS to all, which includes trading. The
    # agent-side MCP must therefore opt in to a bounded read-only list.
    if not explicit_toolsets:
        blockers.append("mcp_toolsets_must_be_explicit")
    if forbidden:
        blockers.append("mcp_write_toolsets_forbidden:" + ",".join(forbidden))
    if "options-data" not in toolsets:
        blockers.append("mcp_options_data_required")
    if not api_key_present:
        blockers.append("alpaca_api_key_missing")
    if not secret_key_present:
        blockers.append("alpaca_secret_key_missing")

    read_only = explicit_toolsets and not forbidden
    return AlpacaMcpReadiness(
        paper_trade=paper_trade,
        explicit_toolsets=explicit_toolsets,
        toolsets=toolsets,
        read_only=read_only,
        api_key_present=api_key_present,
        secret_key_present=secret_key_present,
        command=OFFICIAL_MCP_COMMAND,
        ready=not blockers,
        blockers=tuple(blockers),
    )


def recommended_mcp_env() -> dict[str, str]:
    """Public non-secret settings for the official Alpaca MCP sidecar."""
    return {
        "ALPACA_PAPER_TRADE": "true",
        "ALPACA_TOOLSETS": ",".join(READ_ONLY_TOOLSETS),
    }
