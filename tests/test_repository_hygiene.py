from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", ".pytest_cache", "__pycache__", ".venv", "node_modules"}
FORBIDDEN_PUBLIC_MARKERS = (
    "/home/" + "rlopez",
    "192.168." + "1.",
    "Intel " + ".4",
    "AMD " + ".5",
    "127.0.0.1:" + "18000",
    "test" + "@soindu.com",
)
TEXT_SUFFIXES = {".py", ".md", ".json", ".txt", ".service", ".example", ".toml", ".yml", ".yaml"}


def _public_text_files():
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.name == ".env.example" or path.suffix in TEXT_SUFFIXES:
            yield path


def test_public_repository_contains_no_private_runtime_topology_or_account_identity():
    findings: list[str] = []
    for path in _public_text_files():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for marker in FORBIDDEN_PUBLIC_MARKERS:
            if marker in text:
                findings.append(f"{path.relative_to(ROOT)} contains forbidden marker {marker!r}")
    assert findings == [], "\n".join(findings)


def test_secret_bearing_runtime_files_are_ignored():
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    ignored = {line.strip() for line in gitignore if line.strip() and not line.lstrip().startswith("#")}
    assert ".env" in ignored
    assert ".env.local" in ignored
    assert "secrets/" in ignored
    assert "*.pem" in ignored
    assert "*.key" in ignored


def test_examples_leave_alpaca_credentials_blank():
    for relative in (Path(".env.example"), Path("deploy/runtime.env.example")):
        text = (ROOT / relative).read_text(encoding="utf-8")
        values = {}
        for line in text.splitlines():
            if not line or line.lstrip().startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
        assert values.get("ALPACA_API_KEY") == ""
        assert values.get("ALPACA_SECRET_KEY") == ""
        assert values.get("ALPACA_COMPETITION_ACCOUNT_EMAIL") == ""
