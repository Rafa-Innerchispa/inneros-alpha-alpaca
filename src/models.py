from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TruthState(str, Enum):
    LIVE = "LIVE"
    PAPER_LIVE = "PAPER_LIVE"
    FIXTURE = "FIXTURE"
    PASS = "PASS"
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
    evidence: list[str] = Field(default_factory=list)
    invalidation: str | None = None
    main_risk: str | None = None
    estimated_max_loss: float = Field(ge=0)
    option_symbol: str | None = None
    quantity: int = Field(default=1, ge=1, le=10)
    correlation_id: str


class OptionContractCandidate(BaseModel):
    symbol: str
    underlying_symbol: str
    option_type: Literal["call", "put"]
    strike_price: float
    expiration_date: date
    tradable: bool = True
    bid_price: float = 0
    ask_price: float = 0
    bid_size: int = 0
    ask_size: int = 0
    delta: float | None = None


class ContractSelection(BaseModel):
    status: Literal["SELECTED", "NO_TRADE", "BLOCKED"]
    contract: OptionContractCandidate | None = None
    reason: str
    estimated_max_loss: float = 0
    spread_pct: float | None = None
    candidates_scanned: int = 0
    candidates_eligible: int = 0
    filter_counts: dict[str, int] = Field(default_factory=dict)
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
    day_pl: float = 0
    unrealized_pl: float = 0
    paper: bool = True
    source: TruthState = TruthState.FIXTURE


class TraceEvent(BaseModel):
    ts: datetime = Field(default_factory=utc_now)
    source: str
    from_agent: str
    to_agent: str
    event: str
    status: TruthState
    detail: str
    correlation_id: str


class PipelineRequest(BaseModel):
    ticker: str = "SPY"
    execute: bool = False


class PipelineResult(BaseModel):
    correlation_id: str
    paper_only: bool = True
    snapshot: MarketSnapshot
    intent: TradeIntent
    contract_selection: ContractSelection | None = None
    portfolio: PortfolioView | None = None
    risk: RiskDecision
    execution: ExecutionResult
    trace: list[TraceEvent] = Field(default_factory=list)
