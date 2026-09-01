from __future__ import annotations

from .config import Settings
from .contracts import MarketSnapshot, RiskDecision, TerminalState, TradeIntent


class PaperRiskEngine:
    def __init__(self, settings: Settings):
        self.settings = settings

    def evaluate(self, intent: TradeIntent, snapshot: MarketSnapshot | None = None) -> RiskDecision:
        reasons: list[str] = []
        if not self.settings.alpaca_paper or not intent.paper_only:
            reasons.append("live_trading_disabled: this project is paper-only")
        if intent.symbol not in self.settings.symbol_allowlist:
            reasons.append(f"symbol_not_allowed: {intent.symbol}")
        if intent.qty > self.settings.max_qty:
            reasons.append(f"qty_above_limit: {intent.qty} > {self.settings.max_qty}")

        estimated_notional = None
        price = None
        if intent.limit_price:
            price = intent.limit_price
        elif snapshot:
            price = snapshot.last or snapshot.ask or snapshot.bid
        if price:
            estimated_notional = float(price) * float(intent.qty)
            if estimated_notional > self.settings.max_notional_usd:
                reasons.append(
                    f"notional_above_limit: {estimated_notional:.2f} > {self.settings.max_notional_usd:.2f}"
                )

        allowed = not reasons
        return RiskDecision(
            state=TerminalState.PASS if allowed else TerminalState.BLOCKED,
            allowed=allowed,
            reasons=reasons or ["paper_risk_checks_passed"],
            intent=intent,
            estimated_notional=estimated_notional,
            paper_only=True,
        )
