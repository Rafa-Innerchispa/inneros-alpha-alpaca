from __future__ import annotations

import os
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .mcp_readiness import alpaca_mcp_readiness
from .models import ExecutionResult, MarketSnapshot, PipelineResult, RiskDecision, TradeIntent, TruthState
from .pipeline import PipelineService
from .submission_readiness import submission_readiness


class KillSwitchRequest(BaseModel):
    enabled: bool


app = FastAPI(title="InnerOS Alpha", version="0.7.0")

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
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

pipeline = PipelineService()
adapter = pipeline.adapter
risk_engine = pipeline.risk_engine


@app.get("/health")
def health() -> dict:
    """Fast liveness endpoint. Never probes external services or returns secrets."""
    return {
        "ok": True,
        "service": "inneros-alpha",
        "version": app.version,
        "paper_only": True,
        "alpaca_configured": adapter.configured,
        "kill_switch": pipeline.kill_switch,
        "reasoning_provider": "local-amd-5",
        "reasoning_model": pipeline.reasoner.model,
        "evidence_backend": pipeline.evidence.backend,
        "evidence_last_error": pipeline.evidence.last_error,
    }


@app.get("/ready")
def ready() -> dict:
    """Redacted dependency preflight for demo/runtime orchestration."""
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
    return {
        "ok": analysis_ready,
        "paper_only": True,
        "analysis_ready": analysis_ready,
        "paper_path_ready": paper_path_ready,
        "hackathon_ready": hackathon_ready,
        "paper_execution_armed": bool(paper_path_ready and not pipeline.kill_switch),
        "kill_switch": pipeline.kill_switch,
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


@app.get("/api/mcp/status")
def mcp_status() -> dict:
    """Return the redacted Alpaca MCP safety/readiness contract."""
    return alpaca_mcp_readiness().public_dict()


@app.get("/api/submission/status")
def submission_status() -> dict:
    """Return truthful code-vs-submission readiness without exposing secrets."""
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
def execute(intent: TradeIntent, risk: RiskDecision):
    if pipeline.kill_switch:
        return ExecutionResult(
            status="blocked",
            message="Server kill switch is ON; no broker request sent",
            correlation_id=intent.correlation_id,
        )
    return adapter.submit_order(intent, risk)


@app.post("/api/pipeline/{ticker}", response_model=PipelineResult)
def run_pipeline(ticker: str, execute: bool = False):
    return pipeline.run(ticker=ticker, execute=execute)


@app.get("/api/kill-switch")
def get_kill_switch() -> dict:
    return {"enabled": pipeline.kill_switch, "paper_only": True}


@app.post("/api/kill-switch")
def set_kill_switch(request: KillSwitchRequest) -> dict:
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
