from fastapi.testclient import TestClient

from src.main import app


def _configure(monkeypatch):
    monkeypatch.setenv("INNEROS_JUDGE_AUTH_REQUIRED", "true")
    monkeypatch.setenv("INNEROS_JUDGE_USER", "judge")
    monkeypatch.setenv("INNEROS_JUDGE_PASSWORD", "test-only-password")
    monkeypatch.setenv("INNEROS_JUDGE_SESSION_SECRET", "test-only-session-secret-with-enough-entropy")


def test_judge_auth_redirects_console_and_rejects_api(monkeypatch):
    _configure(monkeypatch)
    client = TestClient(app, base_url="https://testserver")

    console = client.get("/console/", follow_redirects=False)
    assert console.status_code == 303
    assert console.headers["location"].startswith("/login?next=")

    api = client.get("/api/portfolio")
    assert api.status_code == 401
    assert api.json()["detail"] == "Authentication required"


def test_judge_login_sets_secure_http_only_cookie_and_unlocks_console(monkeypatch):
    _configure(monkeypatch)
    client = TestClient(app, base_url="https://testserver")

    response = client.post(
        "/login",
        data={"username": "judge", "password": "test-only-password", "next": "/console/"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/console/"
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie
    assert "Secure" in cookie
    assert "SameSite=lax" in cookie

    console = client.get("/console/")
    assert console.status_code == 200
    assert "Sovereign Opportunity Hunt" in console.text


def test_wrong_judge_password_does_not_create_session(monkeypatch):
    _configure(monkeypatch)
    client = TestClient(app, base_url="https://testserver")

    response = client.post(
        "/login",
        data={"username": "judge", "password": "wrong", "next": "/console/"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "error=1" in response.headers["location"]
    assert "set-cookie" not in response.headers
