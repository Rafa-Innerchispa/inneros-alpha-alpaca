from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class TradeSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class OrderType(StrEnum):
    MARKET = "market"
    LIMIT = "limit"


class TimeInForce(StrEnum):
    DAY = "day"
    GTC = "gtc"


class TerminalState(StrEnum):
    PASS = "PASS"
    BLOCKED = "BLOCKED"
    NO_TRADE = "NO_TRADE"
    FAIL = "FAIL"


class MarketSnapshot(BaseModel):
    symbol: str
    bid: float | None = None
    ask: float | None = None
    last: float | None = None
    source: Literal["FIXTURE", "ALPACA_PAPER", "INNEROS"] = "FIXTURE"
    observed_at: datetime = Field(default_factory=now_utc)
    correlation_id: str = Field(default_factory=lambda: f"corr_{uuid4().hex[:12]}")

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        symbol = value.strip().upper()
        if not symbol:
            raise ValueError("symbol required")
        return symbol


class TradeIntent(BaseModel):
    symbol: str
    side: TradeSide
    qty: float = Field(gt=0)
    order_type: OrderType = OrderType.MARKET
    time_in_force: TimeInForce = TimeInForce.DAY
    limit_price: float | None = Field(default=None, gt=0)
    rationale: str = ""
    correlation_id: str = Field(default_factory=lambda: f"intent_{uuid4().hex[:12]}")
    paper_only: bool = True

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        symbol = value.strip().upper()
        if not symbol:
            raise ValueError("symbol required")
        return symbol


class RiskDecision(BaseModel):
    state: TerminalState
    allowed: bool
    reasons: list[str]
    intent: TradeIntent
    checked_at: datetime = Field(default_factory=now_utc)
    estimated_notional: float | None = None
    paper_only: bool = True


class ExecutionResult(BaseModel):
    state: TerminalState
    intent: TradeIntent
    risk: RiskDecision
    alpaca_order_id: str | None = None
    source: Literal["DRY_RUN", "ALPACA_PAPER"] = "DRY_RUN"
    submitted_at: datetime = Field(default_factory=now_utc)
    evidence: dict[str, Any] = Field(default_factory=dict)


class SessionState(BaseModel):
    correlation_id: str
    mode: Literal["paper"] = "paper"
    market: list[MarketSnapshot] = Field(default_factory=list)
    intents: list[TradeIntent] = Field(default_factory=list)
    decisions: list[RiskDecision] = Field(default_factory=list)
    executions: list[ExecutionResult] = Field(default_factory=list)
