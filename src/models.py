from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TruthState(str, Enum):
    LIVE = "LIVE"
    FIXTURE = "FIXTURE"
    NO_TRADE = "NO_TRADE"
    BLOCKED = "BLOCKED"
    FAIL = "FAIL"


class MarketSnapshot(BaseModel):
    ticker: str
    timestamp: datetime = Field(default_factory=utc_now)
    source: str
    price: float
    freshness_seconds: float = 0
    option_chain_summary: dict = Field(default_factory=dict)
    technicals: dict = Field(default_factory=dict)
    correlation_id: str


class TradeIntent(BaseModel):
    ticker: str
    bias: Literal["BULLISH", "BEARISH", "NEUTRAL"]
    confidence: float = Field(ge=0, le=1)
    strategy: str
    expiry: str | None = None
    dte_target: int | None = None
    delta_target: float | None = None
    rationale: str
    estimated_max_loss: float = Field(ge=0)
    correlation_id: str


class RiskDecision(BaseModel):
    status: Literal["PASS", "NO_TRADE", "BLOCKED"]
    max_loss: float = 0
    portfolio_risk_pct: float = 0
    triggered_gates: list[str] = Field(default_factory=list)
    correlation_id: str


class ExecutionResult(BaseModel):
    status: Literal["submitted", "filled", "rejected", "cancelled", "blocked"]
    alpaca_order_id: str | None = None
    submitted_at: datetime | None = None
    filled_at: datetime | None = None
    message: str = ""
    correlation_id: str


class PortfolioView(BaseModel):
    equity: float
    cash: float
    buying_power: float
    open_positions: int
    paper: bool = True
    source: TruthState = TruthState.FIXTURE
