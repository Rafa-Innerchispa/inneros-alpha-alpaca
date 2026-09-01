from __future__ import annotations

import uuid

from fastapi import FastAPI

from .alpaca_adapter import AlpacaPaperAdapter
from .models import ExecutionResult, MarketSnapshot, RiskDecision, TradeIntent
from .risk import RiskEngine

app = FastAPI(title="InnerOS Alpha", version="0.1.0")
risk_engine = RiskEngine()
adapter = AlpacaPaperAdapter()


@app.get("/health")
def health() -> dict:
    return {"ok": True, "service": "inneros-alpha", "paper_only": True}


@app.get("/api/portfolio")
def portfolio():
    return adapter.get_portfolio()


@app.post("/api/risk", response_model=RiskDecision)
def evaluate_risk(
    snapshot: MarketSnapshot,
    intent: TradeIntent,
    portfolio_equity: float = 100000,
    open_positions: int = 0,
    daily_pnl: float = 0,
    kill_switch: bool = False,
):
    return risk_engine.evaluate(
        snapshot=snapshot,
        intent=intent,
        portfolio_equity=portfolio_equity,
        open_positions=open_positions,
        daily_pnl=daily_pnl,
        kill_switch=kill_switch,
    )


@app.post("/api/execute", response_model=ExecutionResult)
def execute(intent: TradeIntent, risk: RiskDecision):
    return adapter.submit_order(intent, risk)


@app.get("/api/demo/trace")
def demo_trace() -> dict:
    correlation_id = str(uuid.uuid4())
    return {
        "correlation_id": correlation_id,
        "paper_only": True,
        "steps": [
            {"agent": "Market", "status": "NO_TRADE", "source": "FIXTURE"},
            {"agent": "Strategy", "status": "NO_TRADE", "source": "FIXTURE"},
            {"agent": "Risk", "status": "BLOCKED", "source": "DETERMINISTIC"},
            {"agent": "Execution", "status": "NO_TRADE", "source": "PAPER"},
        ],
    }
