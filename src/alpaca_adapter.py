from __future__ import annotations

import os
from datetime import datetime, timezone

import httpx

from .models import ExecutionResult, MarketSnapshot, PortfolioView, RiskDecision, TradeIntent, TruthState


FIXTURE_PRICES = {"SPY": 500.0, "AAPL": 200.0, "NVDA": 120.0}


class AlpacaPaperAdapter:
    """Minimal Alpaca paper adapter.

    The adapter refuses any non-paper trading URL. Market data may be live, but every
    order path is hard-bound to paper-api.alpaca.markets.
    """

    def __init__(self) -> None:
        self.paper = os.getenv("ALPACA_PAPER", "true").lower() == "true"
        self.base_url = os.getenv(
            "ALPACA_API_BASE",
            os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets"),
        ).rstrip("/")
        self.data_url = os.getenv("ALPACA_DATA_BASE", "https://data.alpaca.markets").rstrip("/")
        self.key = os.getenv("ALPACA_KEY_ID", os.getenv("ALPACA_API_KEY", ""))
        self.secret = os.getenv("ALPACA_SECRET_KEY", os.getenv("ALPACA_API_SECRET", ""))
        if not self.paper or self.base_url != "https://paper-api.alpaca.markets":
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
                day_pl=0,
                unrealized_pl=0,
                paper=True,
                source=TruthState.FIXTURE,
            )
        with httpx.Client(timeout=10.0) as client:
            account_response = client.get(f"{self.base_url}/v2/account", headers=self._headers())
            account_response.raise_for_status()
            positions_response = client.get(f"{self.base_url}/v2/positions", headers=self._headers())
            positions_response.raise_for_status()
            account = account_response.json()
            positions = positions_response.json()

        unrealized = sum(float(position.get("unrealized_pl", 0) or 0) for position in positions)
        last_equity = float(account.get("last_equity") or account["equity"])
        equity = float(account["equity"])
        return PortfolioView(
            equity=equity,
            cash=float(account["cash"]),
            buying_power=float(account["buying_power"]),
            open_positions=len(positions),
            day_pl=equity - last_equity,
            unrealized_pl=unrealized,
            paper=True,
            source=TruthState.PAPER_LIVE,
        )

    def get_market_snapshot(self, ticker: str, correlation_id: str) -> MarketSnapshot:
        ticker = ticker.upper().strip()
        if not self.configured:
            return MarketSnapshot(
                ticker=ticker,
                source=TruthState.FIXTURE.value,
                price=FIXTURE_PRICES.get(ticker, 100.0),
                freshness_seconds=0,
                technicals={"mode": "fixture", "note": "No Alpaca paper credentials configured"},
                correlation_id=correlation_id,
            )

        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                f"{self.data_url}/v2/stocks/{ticker}/trades/latest",
                headers=self._headers(),
                params={"feed": "iex"},
            )
            response.raise_for_status()
            trade = response.json()["trade"]
        timestamp = datetime.fromisoformat(str(trade["t"]).replace("Z", "+00:00"))
        freshness = max((datetime.now(timezone.utc) - timestamp).total_seconds(), 0)
        return MarketSnapshot(
            ticker=ticker,
            timestamp=timestamp,
            source=TruthState.LIVE.value,
            price=float(trade["p"]),
            freshness_seconds=freshness,
            technicals={"feed": "iex", "source": "alpaca_latest_trade"},
            correlation_id=correlation_id,
        )

    def submit_order(self, intent: TradeIntent, risk: RiskDecision) -> ExecutionResult:
        if intent.correlation_id != risk.correlation_id:
            return ExecutionResult(
                status="blocked",
                message="Correlation mismatch between intent and risk decision",
                correlation_id=intent.correlation_id,
            )
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
        if intent.strategy not in {"long_call", "long_put"} or not intent.option_symbol:
            return ExecutionResult(
                status="blocked",
                message="No validated long-option contract selected; no order was sent",
                correlation_id=intent.correlation_id,
            )

        payload = {
            "symbol": intent.option_symbol,
            "qty": str(intent.quantity),
            "side": "buy",
            "type": "market",
            "time_in_force": "day",
        }
        submitted_at = datetime.now(timezone.utc)
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(f"{self.base_url}/v2/orders", headers=self._headers(), json=payload)
                response.raise_for_status()
                order = response.json()
            return ExecutionResult(
                status="submitted",
                alpaca_order_id=str(order.get("id") or "") or None,
                submitted_at=submitted_at,
                message="Submitted to Alpaca PAPER endpoint",
                correlation_id=intent.correlation_id,
            )
        except httpx.HTTPError as exc:
            return ExecutionResult(
                status="rejected",
                submitted_at=submitted_at,
                message=f"Alpaca PAPER rejected/failed request: {type(exc).__name__}",
                correlation_id=intent.correlation_id,
            )
