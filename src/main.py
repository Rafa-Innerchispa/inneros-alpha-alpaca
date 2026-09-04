from __future__ import annotations

import base64
import hashlib
import html
import os
import secrets
import time
import uuid
from pathlib import Path
from urllib.parse import parse_qs, quote

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .mcp_readiness import alpaca_mcp_readiness
from .models import ExecutionResult, MarketSnapshot, PipelineResult, RiskDecision, TradeIntent, TruthState
from .pipeline import PipelineService
from .submission_readiness import submission_readiness


class KillSwitchRequest(BaseModel):
    enabled: bool


app = FastAPI(title="InnerOS Alpha", version="0.9.1")

origins = [
    origin.strip()
    for origin in os.getenv(
        "INNEROS_CONSOLE_ORIGINS",
        "http://127.0.0.1:8099,http://localhost:8099,http://127.0.0.1:8088,http://localhost:8088",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-InnerOS-Admin-Token"],
)

pipeline = PipelineService()
adapter = pipeline.adapter
risk_engine = pipeline.risk_engine

SESSION_COOKIE = "inneros_judge_session"
PUBLIC_PATHS = {"/health", "/login", "/api/auth/status"}
DEFAULT_JUDGE_USER = "lablab-judge"
DEFAULT_JUDGE_PBKDF2_ITERATIONS = 310000
DEFAULT_JUDGE_PBKDF2_SALT = "ThlaGJKgxlTCN-ngUpaAHA"
DEFAULT_JUDGE_PBKDF2_HASH = "MoZNbdY_feS5byGZFIeO_vlbviWxAdugrVDY2EhKTlo"
_judge_sessions: dict[str, int] = {}


def _decode_b64url(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + ("=" * (-len(value) % 4)))


def _judge_user() -> str:
    return (os.getenv("INNEROS_JUDGE_USER") or DEFAULT_JUDGE_USER).strip() or DEFAULT_JUDGE_USER


def _judge_auth_configured() -> bool:
    # A strong temporary judge credential is represented only by a PBKDF2 hash in source.
    # Production may override it with server-side INNEROS_JUDGE_USER/PASSWORD values.
    return True


def _judge_auth_required() -> bool:
    return (os.getenv("INNEROS_JUDGE_AUTH_REQUIRED") or "true").strip().lower() == "true"


def _judge_password_valid(candidate: str) -> bool:
    env_password = (os.getenv("INNEROS_JUDGE_PASSWORD") or "").strip()
    if env_password:
        return secrets.compare_digest(candidate, env_password)
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        candidate.encode(),
        _decode_b64url(DEFAULT_JUDGE_PBKDF2_SALT),
        DEFAULT_JUDGE_PBKDF2_ITERATIONS,
    )
    return secrets.compare_digest(derived, _decode_b64url(DEFAULT_JUDGE_PBKDF2_HASH))


def _safe_next(value: str | None) -> str:
    candidate = (value or "/console/").strip()
    if not candidate.startswith("/") or candidate.startswith("//"):
        return "/console/"
    return candidate


def _session_token() -> str:
    ttl = max(int(os.getenv("INNEROS_JUDGE_SESSION_TTL", "21600")), 300)
    token = secrets.token_urlsafe(32)
    _judge_sessions[token] = int(time.time()) + ttl
    return token


def _session_valid(token: str | None) -> bool:
    if not token:
        return False
    expires = _judge_sessions.get(token)
    if expires is None:
        return False
    if expires < int(time.time()):
        _judge_sessions.pop(token, None)
        return False
    return True


def _is_public_path(path: str) -> bool:
    return path in PUBLIC_PATHS or path.startswith("/login?")


@app.middleware("http")
async def judge_access_gate(request: Request, call_next):
    path = request.url.path
    if request.method == "OPTIONS" or _is_public_path(path) or not _judge_auth_required():
        return await call_next(request)
    if _session_valid(request.cookies.get(SESSION_COOKIE)):
        return await call_next(request)
    if path.startswith("/api/"):
        return JSONResponse({"detail": "Authentication required"}, status_code=401)
    target = quote(request.url.path + (f"?{request.url.query}" if request.url.query else ""), safe="/?=&")
    return RedirectResponse(url=f"/login?next={target}", status_code=303)


def _admin_write_gate_configured() -> bool:
    return bool((os.getenv("INNEROS_ADMIN_TOKEN") or "").strip())


def _require_admin_token(provided: str | None) -> None:
    expected = (os.getenv("INNEROS_ADMIN_TOKEN") or "").strip()
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="Admin write gate is not configured; mutable broker controls are disabled",
        )
    candidate = (provided or "").strip()
    if not candidate or not secrets.compare_digest(candidate, expected):
        raise HTTPException(status_code=403, detail="Admin token required")


@app.get("/health")
def health() -> dict:
    """Fast public liveness endpoint. Never probes external services or returns secrets."""
    return {
        "ok": True,
        "service": "inneros-alpha",
        "version": app.version,
        "paper_only": True,
        "alpaca_configured": adapter.configured,
        "kill_switch": pipeline.kill_switch,
        "admin_write_gate_configured": _admin_write_gate_configured(),
        "judge_auth_configured": _judge_auth_configured(),
        "judge_auth_required": _judge_auth_required(),
        "reasoning_provider": "local-amd-5",
        "reasoning_model": pipeline.reasoner.model,
        "evidence_backend": pipeline.evidence.backend,
        "evidence_last_error": pipeline.evidence.last_error,
    }


@app.get("/api/auth/status")
def auth_status() -> dict:
    return {
        "configured": _judge_auth_configured(),
        "required": _judge_auth_required(),
        "protected_console": True,
        "session_cookie": True,
        "credential_storage": "pbkdf2_hash_or_server_runtime_override",
    }


@app.get("/login", response_class=HTMLResponse)
def login_page(next: str = "/console/", error: str = "") -> str:
    message = "Invalid credentials" if error else ""
    target = html.escape(_safe_next(next), quote=True)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>InnerOS Alpha · Judge Access</title>
<style>
*{{box-sizing:border-box}} body{{margin:0;min-height:100vh;display:grid;place-items:center;background:#050a12;color:#eaf7ff;font-family:Inter,system-ui,sans-serif;background-image:radial-gradient(circle at 20% 10%,#07324a 0,transparent 34%),radial-gradient(circle at 80% 80%,#102453 0,transparent 34%)}}
.shell{{width:min(92vw,520px);padding:34px;border:1px solid #1d5874;background:rgba(5,14,25,.92);box-shadow:0 24px 80px #0009;border-radius:22px}} .k{{font-size:12px;letter-spacing:.18em;color:#62e6ff;text-transform:uppercase}} h1{{font-size:34px;margin:10px 0 8px}} p{{color:#a8c5d4;line-height:1.55}} .badges{{display:flex;gap:8px;flex-wrap:wrap;margin:18px 0}} .b{{font-size:11px;border:1px solid #27657d;border-radius:999px;padding:7px 10px;color:#8feaff;background:#082233}} label{{display:block;margin:15px 0 6px;color:#bdd7e3;font-size:13px}} input{{width:100%;padding:13px 14px;background:#07121e;color:white;border:1px solid #285269;border-radius:10px;outline:none}} input:focus{{border-color:#4de1ff;box-shadow:0 0 0 3px #2ac5e522}} button{{margin-top:18px;width:100%;padding:14px;border:0;border-radius:10px;background:linear-gradient(135deg,#50e8ff,#4d85ff);font-weight:800;color:#031019;cursor:pointer}} .err{{color:#ff9c9c;min-height:20px}}
</style></head><body><main class="shell"><div class="k">Sovereign Financial Agents · Judge Portal</div><h1>InnerOS Alpha</h1><p>Protected access to a local-first Alpaca PAPER control plane. Reasoning runs on owned AMD infrastructure. Broker credentials never enter the LLM.</p><div class="badges"><span class="b">LOCAL QWEN</span><span class="b">ALPACA MCP READ ONLY</span><span class="b">PAPER ONLY</span><span class="b">AUDITED</span></div><div class="err">{html.escape(message)}</div><form method="post" action="/login"><input type="hidden" name="next" value="{target}"><label>Judge username</label><input name="username" autocomplete="username" required autofocus><label>Password</label><input name="password" type="password" autocomplete="current-password" required><button type="submit">ENTER SOVEREIGN CONSOLE</button></form></main></body></html>"""


@app.post("/login")
async def login_submit(request: Request):
    body = (await request.body()).decode(errors="ignore")
    form = parse_qs(body)
    username = (form.get("username") or [""])[0]
    password = (form.get("password") or [""])[0]
    target = _safe_next((form.get("next") or ["/console/"])[0])
    if not (secrets.compare_digest(username, _judge_user()) and _judge_password_valid(password)):
        return RedirectResponse(url=f"/login?next={quote(target, safe='/')}&error=1", status_code=303)
    response = RedirectResponse(url=target, status_code=303)
    response.set_cookie(
        SESSION_COOKIE,
        _session_token(),
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=max(int(os.getenv("INNEROS_JUDGE_SESSION_TTL", "21600")), 300),
        path="/",
    )
    return response


@app.get("/logout")
def logout(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        _judge_sessions.pop(token, None)
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


@app.get("/ready")
def ready() -> dict:
    reasoning = pipeline.reasoner.status()
    analysis_ready = bool(reasoning.get("reachable") and reasoning.get("model_available"))
    mcp = alpaca_mcp_readiness()

    alpaca_reachable = False
    alpaca_error = None
    if adapter.configured:
        try:
            portfolio_view = adapter.get_portfolio()
            alpaca_reachable = portfolio_view.source == TruthState.PAPER_LIVE
        except Exception as exc:
            alpaca_error = type(exc).__name__

    paper_path_ready = bool(analysis_ready and alpaca_reachable)
    hackathon_ready = bool(paper_path_ready and mcp.ready)
    admin_gate = _admin_write_gate_configured()
    return {
        "ok": analysis_ready,
        "paper_only": True,
        "analysis_ready": analysis_ready,
        "paper_path_ready": paper_path_ready,
        "hackathon_ready": hackathon_ready,
        "paper_execution_armed": bool(paper_path_ready and not pipeline.kill_switch and admin_gate),
        "kill_switch": pipeline.kill_switch,
        "admin_write_gate_configured": admin_gate,
        "judge_auth_configured": _judge_auth_configured(),
        "judge_auth_required": _judge_auth_required(),
        "reasoning": reasoning,
        "alpaca": {
            "credentials_present": adapter.configured,
            "paper_api_reachable": alpaca_reachable,
            "error": alpaca_error,
        },
        "alpaca_mcp": mcp.public_dict(),
        "submission": submission_readiness().public_dict(),
        "console": {"mounted": True, "path": "/console/"},
    }


@app.get("/api/sovereignty")
def sovereignty() -> dict:
    policy = risk_engine.policy
    return {
        "local_reasoning": {
            "provider": "local-amd-5",
            "runtime": "vllm",
            "model": pipeline.reasoner.model,
            "owned_infrastructure": True,
            "broker_credentials_visible_to_llm": False,
        },
        "data_boundary": {
            "market_source": "Alpaca",
            "reasoning_location": "owner-controlled local AMD infrastructure",
            "external_llm_calls": False,
            "evidence_persisted_locally": True,
        },
        "authority": {
            "alpaca_mcp_read_only": True,
            "contract_selection": "deterministic",
            "risk_engine": "deterministic",
            "paper_only": True,
            "kill_switch": pipeline.kill_switch,
        },
        "risk_policy": {
            "max_risk_per_trade_pct": policy.max_risk_per_trade_pct,
            "max_daily_loss_pct": policy.max_daily_loss_pct,
            "max_open_positions": policy.max_open_positions,
            "min_dte": policy.min_dte,
            "max_dte": policy.max_dte,
            "max_snapshot_age_seconds": policy.max_snapshot_age_seconds,
        },
    }


@app.get("/api/mcp/status")
def mcp_status() -> dict:
    return alpaca_mcp_readiness().public_dict()


@app.get("/api/submission/status")
def submission_status() -> dict:
    return submission_readiness().public_dict()


@app.get("/")
def root():
    return RedirectResponse(url="/console/", status_code=307)


@app.get("/api/portfolio")
def portfolio():
    return adapter.get_portfolio()


@app.get("/api/market/{ticker}", response_model=MarketSnapshot)
def market(ticker: str):
    return adapter.get_market_snapshot(ticker=ticker, correlation_id=str(uuid.uuid4()))


@app.get("/api/intent/{ticker}", response_model=TradeIntent)
def intent(ticker: str):
    correlation_id = str(uuid.uuid4())
    snapshot = adapter.get_market_snapshot(ticker=ticker, correlation_id=correlation_id)
    return pipeline.reasoner.propose(snapshot)


@app.post("/api/risk", response_model=RiskDecision)
def evaluate_risk(
    snapshot: MarketSnapshot,
    intent: TradeIntent,
    portfolio_equity: float = 100000,
    open_positions: int = 0,
    daily_pnl: float = 0,
    kill_switch: bool | None = None,
):
    return risk_engine.evaluate(
        snapshot=snapshot,
        intent=intent,
        portfolio_equity=portfolio_equity,
        open_positions=open_positions,
        daily_pnl=daily_pnl,
        kill_switch=pipeline.kill_switch if kill_switch is None else kill_switch,
    )


@app.post("/api/execute", response_model=ExecutionResult)
def execute(
    intent: TradeIntent,
    risk: RiskDecision,
    x_inneros_admin_token: str | None = Header(default=None, alias="X-InnerOS-Admin-Token"),
):
    _require_admin_token(x_inneros_admin_token)
    if pipeline.kill_switch:
        return ExecutionResult(
            status="blocked",
            message="Server kill switch is ON; no broker request sent",
            correlation_id=intent.correlation_id,
        )
    return adapter.submit_order(intent, risk)


@app.post("/api/pipeline/{ticker}", response_model=PipelineResult)
def run_pipeline(
    ticker: str,
    execute: bool = False,
    x_inneros_admin_token: str | None = Header(default=None, alias="X-InnerOS-Admin-Token"),
):
    if execute:
        _require_admin_token(x_inneros_admin_token)
    return pipeline.run(ticker=ticker, execute=execute)


@app.get("/api/kill-switch")
def get_kill_switch() -> dict:
    return {"enabled": pipeline.kill_switch, "paper_only": True}


@app.post("/api/kill-switch")
def set_kill_switch(
    request: KillSwitchRequest,
    x_inneros_admin_token: str | None = Header(default=None, alias="X-InnerOS-Admin-Token"),
) -> dict:
    _require_admin_token(x_inneros_admin_token)
    enabled = pipeline.set_kill_switch(request.enabled)
    return {"enabled": enabled, "paper_only": True}


@app.get("/api/trace/{correlation_id}")
def trace(correlation_id: str) -> dict:
    events = pipeline.get_trace(correlation_id)
    if not events:
        raise HTTPException(status_code=404, detail="Trace not found")
    return {"correlation_id": correlation_id, "events": events}


@app.get("/api/evidence/{correlation_id}")
def evidence(correlation_id: str) -> dict:
    document = pipeline.get_evidence(correlation_id)
    if not document:
        raise HTTPException(status_code=404, detail="Evidence not found")
    return document


CONSOLE_DIR = Path(__file__).resolve().parents[1] / "apps" / "console"
if CONSOLE_DIR.is_dir():
    app.mount("/console", StaticFiles(directory=str(CONSOLE_DIR), html=True), name="console")
