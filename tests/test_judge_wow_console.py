from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONSOLE = ROOT / "apps" / "console"


def test_judge_wow_console_exposes_live_and_verified_modes():
    html = (CONSOLE / "index.html").read_text(encoding="utf-8")
    assert "RUN LIVE MARKET DECISION" in html
    assert "REPLAY VERIFIED PAPER PROOF" in html
    assert "HISTORICAL · VERIFIED" in html
    assert "SPY260930C00779000" in html
    assert "6e1cc1de-821c-49e1-8605-c8161caf1a05" in html
    assert "8006ee08-104a-4bcc-91c7-1013ae4b1a41" in html


def test_public_console_remains_analysis_only_and_replay_is_local():
    api_client = (CONSOLE / "api-client.js").read_text(encoding="utf-8")
    console_js = (CONSOLE / "console.js").read_text(encoding="utf-8")

    assert "/api/pipeline/${symbol}?execute=false" in api_client
    assert "console_never_submits_fills" in api_client
    assert 'const VERIFIED_PROOF = {' in console_js
    assert "replayVerifiedProof" in console_js
    assert "api.submitPaperOrder" not in console_js
    assert 'setTruth("PASS", "Historical verified PAPER proof' in console_js


def test_runtime_proof_badges_are_backed_by_read_only_status_calls():
    api_client = (CONSOLE / "api-client.js").read_text(encoding="utf-8")
    console_js = (CONSOLE / "console.js").read_text(encoding="utf-8")

    assert 'ready() { return request("/ready"); }' in api_client
    assert 'mcpStatus() { return request("/api/mcp/status"); }' in api_client
    assert "mcp?.ready && mcp?.read_only" in console_js
    assert "ready?.kill_switch" in console_js
