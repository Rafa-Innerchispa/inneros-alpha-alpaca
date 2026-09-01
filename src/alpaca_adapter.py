from __future__ import annotations

import os
from datetime import datetime, timezone

import httpx

from .models import ExecutionResult, PortfolioView, RiskDecision, TradeIntent, TruthState


class AlpacaPaperAdapter:
    def __init__(self) -> None:
        self.paper = os.getenv("ALPACA_PAPER", "true").lower() == "true"
        self.base_url = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets").rstrip("/")
        self.key = os.getenv("ALPACA_API_KEY", "")
        self.secret = os.getenv("ALPACA_API_SECRET", "")
        if not self.paper or "paper-api.alpaca.markets" not in self.base_url:
            raise RuntimeError("Paper-only guard: live trading endpoint is forbidden")

    @property
    def configured(self) -> bool:
        return bool(self.key and self.secret)

    def _headers(self) -> dict[str, str]:
        return {
            "APCA-API-KEY-ID": self.key,
            "APCA-API-SECRET-KEY": self.secret,
        }

    def get_portfolio(self) -> PortfolioView:
        if not self.configured:
            return PortfolioView(
                equity=100000,
                cash=100000,
                buying_power=200000,
                open_positions=0,
                paper=True,
                source=TruthState.FIXTURE,
            )
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{self.base_url}/v2/account", headers=self._headers())
            response.raise_for_status()
            data = response.json()
        return PortfolioView(
            equity=float(data["equity"]),
            cash=float(data["cash"]),
            buying_power=float(data["buying_power"]),
            open_positions=0,
            paper=True,
            source=TruthState.LIVE,
        )

    def submit_order(self, intent: TradeIntent, risk: RiskDecision) -> ExecutionResult:
        if risk.status != "PASS":
            return ExecutionResult(
                status="blocked",
                message=f"Risk gate returned {risk.status}",
                correlation_id=intent.correlation_id,
            )
        if not self.configured:
            return ExecutionResult(
                status="blocked",
                message="Alpaca paper credentials are not configured; no order was sent",
                correlation_id=intent.correlation_id,
            )
        return ExecutionResult(
            status="blocked",
            message="Order construction is intentionally disabled until option contract selection is implemented",
            submitted_at=datetime.now(timezone.utc),
            correlation_id=intent.correlation_id,
        )
