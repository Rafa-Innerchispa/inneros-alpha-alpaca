from pathlib import Path


def test_console_renders_deterministic_contract_selection_step():
    javascript = Path("apps/console/console.js").read_text()
    fixture = Path("apps/console/fixtures/session.json").read_text()
    assert 'label: "Contract"' in javascript
    assert "contract_selection" in javascript
    assert '"label": "Contract"' in fixture
    assert "No contract symbol is invented" in fixture
