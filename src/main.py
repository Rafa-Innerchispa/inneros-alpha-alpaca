from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .models import ExecutionResult, MarketSnapshot, PipelineResult, RiskDecision, TradeIntent
from .pipeline import PipelineService


class KillSwitchRequest(BaseModel):
    enabled: bool


app = FastAPI(title="InnerOS Alpha", version="0.2.0")

origins = [
    origin.strip()
    for origin in os.getenv(
        "INNEROS_CONSOLE_ORIGINS",
        "http://127.0.0.1:8099,http://localhost:8099",
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
    return {
        "ok": True,
        "service": "inneros-alpha",
        "version": app.version,
        "paper_only": True,
        "alpaca_configured": adapter.configured,
        "kill_switch": pipeline.kill_switch,
        "reasoning_model": pipeline.reasoner.model,
        "reasoning_url": pipeline.reasoner.base_url,
    }


@app.get("/api/portfolio")
def portfolio():
    return adapter.get_portfolio()


@app.get("/api/market/{ticker}", response_model=MarketSnapshot)
def market(ticker: str):
    import uuid

    return adapter.get_market_snapshot(ticker=ticker, correlation_id=str(uuid.uuid4()))


@app.get("/api/intent/{ticker}", response_model=TradeIntent)
def intent(ticker: str):
    import uuid

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
