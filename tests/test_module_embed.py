import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_manifest_embed_and_paper_only_contract():
    manifest = json.loads((ROOT / "inneros.module.json").read_text())
    assert manifest["schema_version"] == "inneros.module.v1"
    assert manifest["module_id"] == "alpha.trading.alpaca"
    assert manifest["security"]["paper_only"] is True
    assert manifest["security"]["real_money_allowed"] is False
    assert manifest["security"]["auth_required_when_embedded"] is True
    assert manifest["security"]["console_never_submits_fills"] is True
    assert manifest["security"]["embed_post_message"] == "inneros.module.ready"
    assert manifest["security"]["llm_can_select_contract_symbol"] is False
    assert manifest["entrypoints"]["health"] == "/health"
    assert "embed" in manifest["routes"]["embed_query"]
    assert "require_gateway" in manifest["routes"]["embed_query"]


def test_console_api_client_is_analysis_only_and_embed_aware():
    client = (ROOT / "apps/console/api-client.js").read_text()
    console = (ROOT / "apps/console/console.js").read_text()
    shell = (ROOT / "apps/console/module-shell.js").read_text()
    index = (ROOT / "apps/console/index.html").read_text()
    assert "execute=false" in client
    assert "console_never_submits_fills" in client
    assert 'label: "Contract"' in console
    assert "/api/execute" not in console
    assert "gateway_token_missing" in shell
    assert "inneros.module.ready" in shell
    assert "module-shell.js" in index
    assert "api-client.js" in index
