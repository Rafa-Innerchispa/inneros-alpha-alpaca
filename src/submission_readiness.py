"""Truthful hackathon submission readiness for InnerOS Alpha.

This module intentionally separates code readiness from submission readiness.
A build can be technically sound while the dedicated competition account,
live PAPER evidence, video, or final write-up are still pending.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import os
from pathlib import Path
from typing import Mapping

from .mcp_readiness import alpaca_mcp_readiness


def _env_bool(values: Mapping[str, str], key: str, default: bool = False) -> bool:
    raw = values.get(key)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class SubmissionReadiness:
    code_ready: bool
    submission_ready: bool
    paper_only: bool
    paper_api_credentials_present: bool
    mcp_policy_safe: bool
    mcp_live_ready: bool
    competition_account_declared_dedicated: bool
    competition_initial_100k_verified: bool
    paper_e2e_verified: bool
    writeup_present: bool
    writeup_finalized: bool
    demo_video_present: bool
    competition_account_email_present: bool
    blockers: tuple[str, ...]

    def public_dict(self) -> dict[str, object]:
        """Public-safe projection. Never emit account email or credential values."""
        payload = asdict(self)
        payload["blockers"] = list(self.blockers)
        return payload


def submission_readiness(
    env: Mapping[str, str] | None = None,
    *,
    repo_root: Path | None = None,
) -> SubmissionReadiness:
    values: Mapping[str, str] = os.environ if env is None else env
    root = repo_root or Path(__file__).resolve().parents[1]

    app_paper = _env_bool(values, "ALPACA_PAPER", default=True)
    mcp = alpaca_mcp_readiness(values)
    paper_only = bool(app_paper and mcp.paper_trade)

    api_key_present = bool((values.get("ALPACA_API_KEY") or values.get("ALPACA_KEY_ID") or "").strip())
    secret_present = bool((values.get("ALPACA_SECRET_KEY") or values.get("ALPACA_API_SECRET") or "").strip())
    paper_api_credentials_present = bool(api_key_present and secret_present)

    # MCP policy safety is independent from credentials. This lets the build be
    # code-ready while still refusing to call a broker until secrets are injected.
    mcp_policy_blockers = {
        "mcp_live_trading_forbidden",
        "mcp_toolsets_must_be_explicit",
        "mcp_options_data_required",
    }
    mcp_policy_safe = bool(
        mcp.paper_trade
        and mcp.explicit_toolsets
        and mcp.read_only
        and "options-data" in mcp.toolsets
        and not any(
            blocker in mcp_policy_blockers or blocker.startswith("mcp_write_toolsets_forbidden:")
            for blocker in mcp.blockers
        )
    )

    dedicated = _env_bool(values, "ALPACA_COMPETITION_ACCOUNT_DEDICATED", default=False)
    initial_100k_verified = _env_bool(values, "ALPACA_COMPETITION_INITIAL_BALANCE_VERIFIED", default=False)
    paper_e2e_verified = _env_bool(values, "ALPACA_PAPER_E2E_VERIFIED", default=False)
    writeup_finalized = _env_bool(values, "INNEROS_ALPHA_WRITEUP_FINALIZED", default=False)
    demo_video_present = bool((values.get("INNEROS_ALPHA_DEMO_VIDEO_URL") or "").strip())
    email_present = bool((values.get("ALPACA_COMPETITION_ACCOUNT_EMAIL") or "").strip())
    writeup_present = (root / "docs" / "SUBMISSION_WRITEUP.md").is_file()

    code_ready = bool(paper_only and mcp_policy_safe and writeup_present)

    blockers: list[str] = []
    if not code_ready:
        if not paper_only:
            blockers.append("paper_only_guard_not_ready")
        if not mcp_policy_safe:
            blockers.append("mcp_read_only_policy_not_ready")
        if not writeup_present:
            blockers.append("submission_writeup_missing")
    if not dedicated:
        blockers.append("dedicated_competition_account_not_declared")
    if not email_present:
        blockers.append("competition_account_email_not_configured")
    if not initial_100k_verified:
        blockers.append("competition_initial_100k_not_verified")
    if not paper_api_credentials_present:
        blockers.append("paper_api_credentials_missing")
    if not mcp.ready:
        blockers.append("alpaca_mcp_live_not_ready")
    if not paper_e2e_verified:
        blockers.append("controlled_paper_e2e_not_verified")
    if not writeup_finalized:
        blockers.append("submission_writeup_not_finalized")
    if not demo_video_present:
        blockers.append("demo_video_missing")

    return SubmissionReadiness(
        code_ready=code_ready,
        submission_ready=not blockers,
        paper_only=paper_only,
        paper_api_credentials_present=paper_api_credentials_present,
        mcp_policy_safe=mcp_policy_safe,
        mcp_live_ready=mcp.ready,
        competition_account_declared_dedicated=dedicated,
        competition_initial_100k_verified=initial_100k_verified,
        paper_e2e_verified=paper_e2e_verified,
        writeup_present=writeup_present,
        writeup_finalized=writeup_finalized,
        demo_video_present=demo_video_present,
        competition_account_email_present=email_present,
        blockers=tuple(blockers),
    )
