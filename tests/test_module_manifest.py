import json
from pathlib import Path


def test_inneros_module_manifest_is_portable_and_paper_only():
    manifest = json.loads(Path("inneros.module.json").read_text())
    assert manifest["schema_version"] == "inneros.module.v1"
    assert manifest["project_id"] == "inneros-alpha-alpaca"
    assert manifest["repo"] == "Rafa-Innerchispa/inneros-alpha-alpaca"
    assert manifest["security"]["paper_only"] is True
    assert manifest["security"]["real_money_allowed"] is False
    assert manifest["security"]["kill_switch_default"] is True
    strategy = next(agent for agent in manifest["agents"] if agent["id"] == "strategy-agent")
    assert strategy["runtime"] == "local-amd-5"
    assert "Qwen3-Coder" in strategy["model"]
