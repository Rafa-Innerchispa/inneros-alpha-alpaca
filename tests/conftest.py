import pytest


@pytest.fixture(autouse=True)
def disable_judge_auth_by_default(monkeypatch):
    """Keep legacy unit tests focused on API contracts; auth has dedicated tests."""
    monkeypatch.setenv("INNEROS_JUDGE_AUTH_REQUIRED", "false")
