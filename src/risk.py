from __future__ import annotations

from dataclasses import dataclass

from .models import MarketSnapshot, RiskDecision, TradeIntent


@dataclass(frozen=True)
class RiskPolicy:
    max_risk_per_trade_pct: float = 1.0
    max_daily_loss_pct: float = 3.0
    max_open_positions: int = 4
    min_dte: int = 14
    max_dte: int = 45
    max_snapshot_age_seconds: float = 30.0


class RiskEngine:
    def __init__(self, policy: RiskPolicy | None = None) -> None:
        self.policy = policy or RiskPolicy()
        self._seen_correlation_ids: set[str] = set()

    def evaluate(
        self,
        *,
        snapshot: MarketSnapshot,
        intent: TradeIntent,
        portfolio_equity: float,
        open_positions: int,
        daily_pnl: float,
        kill_switch: bool = False,
    ) -> RiskDecision:
        gates: list[str] = []

        if kill_switch:
            gates.append("KILL_SWITCH")
        if snapshot.freshness_seconds > self.policy.max_snapshot_age_seconds:
            gates.append("STALE_MARKET_DATA")
        if intent.correlation_id in self._seen_correlation_ids:
            gates.append("DUPLICATE_INTENT")
        if open_positions >= self.policy.max_open_positions:
            gates.append("MAX_OPEN_POSITIONS")
        if portfolio_equity <= 0:
            gates.append("INVALID_PORTFOLIO_EQUITY")
        if daily_pnl < -(portfolio_equity * self.policy.max_daily_loss_pct / 100):
            gates.append("DAILY_LOSS_CAP")
        if intent.dte_target is not None and not (self.policy.min_dte <= intent.dte_target <= self.policy.max_dte):
            gates.append("DTE_OUT_OF_RANGE")

        allowed_max_loss = max(portfolio_equity, 0) * self.policy.max_risk_per_trade_pct / 100
        if intent.estimated_max_loss > allowed_max_loss:
            gates.append("MAX_RISK_PER_TRADE")

        if gates:
            return RiskDecision(
                status="BLOCKED",
                max_loss=allowed_max_loss,
                portfolio_risk_pct=self.policy.max_risk_per_trade_pct,
                triggered_gates=gates,
                correlation_id=intent.correlation_id,
            )

        if intent.bias == "NEUTRAL" or intent.confidence < 0.55:
            return RiskDecision(
                status="NO_TRADE",
                max_loss=allowed_max_loss,
                portfolio_risk_pct=self.policy.max_risk_per_trade_pct,
                triggered_gates=["INSUFFICIENT_CONVICTION"],
                correlation_id=intent.correlation_id,
            )

        self._seen_correlation_ids.add(intent.correlation_id)
        return RiskDecision(
            status="PASS",
            max_loss=allowed_max_loss,
            portfolio_risk_pct=self.policy.max_risk_per_trade_pct,
            triggered_gates=[],
            correlation_id=intent.correlation_id,
        )
