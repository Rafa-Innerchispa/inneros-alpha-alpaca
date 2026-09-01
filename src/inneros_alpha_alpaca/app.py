from __future__ import annotations

from fastapi import FastAPI

from .alpaca_adapter import AlpacaPaperAdapter
from .config import Settings
from .contracts import ExecutionResult, MarketSnapshot, SessionState, TradeIntent
from .risk import PaperRiskEngine
from .storage import EvidenceStore

settings = Settings()
app = FastAPI(title="InnerOS Alpha Alpaca", version="0.2.0")


@app.get("/health")
def health() -> dict:
    adapter = AlpacaPaperAdapter(settings)
    return {
        "ok": True,
        "service": "inneros-alpha-alpaca",
        "mode": "paper",
        "paper_only": settings.alpaca_paper,
        "alpaca": adapter.ready(),
        "reasoning_url": settings.inneros_reasoning_url,
    }


@app.get("/api/account")
async def account() -> dict:
    return await AlpacaPaperAdapter(settings).get_account()


@app.get("/api/positions")
async def positions() -> dict:
    return await AlpacaPaperAdapter(settings).get_positions()


@app.get("/api/session", response_model=SessionState)
def session(correlation_id: str = "demo") -> SessionState:
    market = [
        MarketSnapshot(symbol="SPY", bid=550.0, ask=550.2, last=550.1, correlation_id=correlation_id),
        MarketSnapshot(symbol="QQQ", bid=470.0, ask=470.4, last=470.2, correlation_id=correlation_id),
    ]
    return SessionState(correlation_id=correlation_id, market=market)


@app.post("/api/intents/evaluate")
def evaluate_intent(intent: TradeIntent, last_price: float | None = None) -> dict:
    snapshot = None
    if last_price:
        snapshot = MarketSnapshot(symbol=intent.symbol, last=last_price, correlation_id=intent.correlation_id)
    risk = PaperRiskEngine(settings).evaluate(intent, snapshot=snapshot)
    EvidenceStore(settings).persist("risk_decisions", risk.model_dump(mode="json"))
    return risk.model_dump(mode="json")


@app.post("/api/orders/paper", response_model=ExecutionResult)
async def submit_paper_order(intent: TradeIntent, last_price: float | None = None) -> ExecutionResult:
    snapshot = None
    if last_price:
        snapshot = MarketSnapshot(symbol=intent.symbol, last=last_price, correlation_id=intent.correlation_id)
    risk = PaperRiskEngine(settings).evaluate(intent, snapshot=snapshot)
    result = await AlpacaPaperAdapter(settings).submit_order(intent, risk)
    EvidenceStore(settings).persist("executions", result.model_dump(mode="json"))
    return result
