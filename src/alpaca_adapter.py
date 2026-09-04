from __future__ import annotations

import math
import os
import statistics
from datetime import date, datetime, timedelta, timezone

import httpx

from .models import (
    ExecutionResult,
    MarketSnapshot,
    OptionContractCandidate,
    PortfolioView,
    RiskDecision,
    TradeIntent,
    TruthState,
)


FIXTURE_PRICES = {"SPY": 500.0, "AAPL": 200.0, "NVDA": 120.0}


class AlpacaPaperAdapter:
    """Alpaca adapter with an immutable PAPER-only trading boundary.

    Market/option data can be read from Alpaca data services. Any order write is
    hard-bound to https://paper-api.alpaca.markets and fails closed otherwise.
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

    @staticmethod
    def _pct_return(closes: list[float], bars_back: int) -> float | None:
        if len(closes) <= bars_back or closes[-1 - bars_back] <= 0:
            return None
        return ((closes[-1] / closes[-1 - bars_back]) - 1.0) * 100.0

    @classmethod
    def _technical_packet(cls, bars: list[dict]) -> dict:
        closes = [float(bar.get("c") or 0) for bar in bars if float(bar.get("c") or 0) > 0]
        highs = [float(bar.get("h") or 0) for bar in bars if float(bar.get("h") or 0) > 0]
        lows = [float(bar.get("l") or 0) for bar in bars if float(bar.get("l") or 0) > 0]
        volumes = [float(bar.get("v") or 0) for bar in bars]
        if not closes:
            return {"bars_available": False, "bar_count": 0}

        r5 = cls._pct_return(closes, 5)
        r15 = cls._pct_return(closes, 15)
        r60 = cls._pct_return(closes, 60)
        if r15 is not None and r60 is not None and r15 > 0 and r60 > 0:
            trend = "BULLISH"
        elif r15 is not None and r60 is not None and r15 < 0 and r60 < 0:
            trend = "BEARISH"
        else:
            trend = "MIXED"

        log_returns: list[float] = []
        for previous, current in zip(closes[-61:-1], closes[-60:]):
            if previous > 0 and current > 0:
                log_returns.append(math.log(current / previous))
        minute_vol_pct = statistics.pstdev(log_returns) * 100 if len(log_returns) >= 2 else None
        range_pct = None
        if highs and lows and closes[-1] > 0:
            range_pct = ((max(highs) - min(lows)) / closes[-1]) * 100

        return {
            "bars_available": True,
            "bar_count": len(bars),
            "return_5m_pct": None if r5 is None else round(r5, 4),
            "return_15m_pct": None if r15 is None else round(r15, 4),
            "return_60m_pct": None if r60 is None else round(r60, 4),
            "sample_move_pct": round(((closes[-1] / closes[0]) - 1.0) * 100, 4) if closes[0] > 0 else None,
            "sample_range_pct": None if range_pct is None else round(range_pct, 4),
            "minute_return_vol_pct": None if minute_vol_pct is None else round(minute_vol_pct, 4),
            "volume_last_60_bars": int(sum(volumes[-60:])),
            "trend": trend,
            "bar_source": "alpaca_iex_1min",
            "bar_asof": str(bars[-1].get("t") or ""),
        }

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

        technicals: dict = {"feed": "iex", "source": "alpaca_latest_trade"}
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                f"{self.data_url}/v2/stocks/{ticker}/trades/latest",
                headers=self._headers(),
                params={"feed": "iex"},
            )
            response.raise_for_status()
            trade = response.json()["trade"]

            try:
                bars_response = client.get(
                    f"{self.data_url}/v2/stocks/{ticker}/bars",
                    headers=self._headers(),
                    params={
                        "timeframe": "1Min",
                        "start": (datetime.now(timezone.utc) - timedelta(days=5)).isoformat(),
                        "limit": 120,
                        "feed": "iex",
                        "adjustment": "raw",
                    },
                )
                bars_response.raise_for_status()
                bars_payload = bars_response.json()
                technicals.update(self._technical_packet(list(bars_payload.get("bars") or [])))
            except Exception as exc:
                technicals.update({
                    "bars_available": False,
                    "bars_error": type(exc).__name__,
                    "note": "Latest trade is live; recent bar features were unavailable and were not fabricated.",
                })

        timestamp = datetime.fromisoformat(str(trade["t"]).replace("Z", "+00:00"))
        freshness = max((datetime.now(timezone.utc) - timestamp).total_seconds(), 0)
        return MarketSnapshot(
            ticker=ticker,
            timestamp=timestamp,
            source=TruthState.LIVE.value,
            price=float(trade["p"]),
            freshness_seconds=freshness,
            technicals=technicals,
            correlation_id=correlation_id,
        )

    @staticmethod
    def _quote_fields(snapshot: dict) -> tuple[float, float, int, int]:
        quote = snapshot.get("latestQuote") or snapshot.get("latest_quote") or {}
        bid = float(quote.get("bp") or quote.get("bid_price") or 0)
        ask = float(quote.get("ap") or quote.get("ask_price") or 0)
        bid_size = int(quote.get("bs") or quote.get("bid_size") or 0)
        ask_size = int(quote.get("as") or quote.get("ask_size") or 0)
        return bid, ask, bid_size, ask_size

    @staticmethod
    def _delta(snapshot: dict) -> float | None:
        greeks = snapshot.get("greeks") or {}
        value = greeks.get("delta")
        return None if value is None else float(value)

    def get_option_candidates(
        self,
        *,
        ticker: str,
        option_type: str,
        underlying_price: float,
        min_dte: int = 14,
        max_dte: int = 45,
        today: date | None = None,
    ) -> list[OptionContractCandidate]:
        """Read active contract metadata plus current quotes/Greeks from Alpaca."""
        if not self.configured:
            return []
        ticker = ticker.upper().strip()
        option_type = option_type.lower().strip()
        if option_type not in {"call", "put"}:
            return []
        today = today or date.today()
        start = today + timedelta(days=min_dte)
        end = today + timedelta(days=max_dte)
        strike_min = max(underlying_price * 0.90, 0.01)
        strike_max = underlying_price * 1.10

        contract_params = {
            "underlying_symbols": ticker,
            "status": "active",
            "type": option_type,
            "expiration_date_gte": start.isoformat(),
            "expiration_date_lte": end.isoformat(),
            "strike_price_gte": f"{strike_min:.4f}",
            "strike_price_lte": f"{strike_max:.4f}",
            "limit": 1000,
        }
        snapshot_params = {
            "type": option_type,
            "expiration_date_gte": start.isoformat(),
            "expiration_date_lte": end.isoformat(),
            "strike_price_gte": f"{strike_min:.4f}",
            "strike_price_lte": f"{strike_max:.4f}",
            "limit": 1000,
        }

        with httpx.Client(timeout=12.0) as client:
            contracts_response = client.get(
                f"{self.base_url}/v2/options/contracts",
                headers=self._headers(),
                params=contract_params,
            )
            contracts_response.raise_for_status()
            contracts_payload = contracts_response.json()

            snapshots_response = client.get(
                f"{self.data_url}/v1beta1/options/snapshots/{ticker}",
                headers=self._headers(),
                params=snapshot_params,
            )
            snapshots_response.raise_for_status()
            snapshots_payload = snapshots_response.json()

        snapshots = snapshots_payload.get("snapshots") or {}
        candidates: list[OptionContractCandidate] = []
        for raw in contracts_payload.get("option_contracts", []):
            symbol = str(raw.get("symbol") or "")
            if not symbol:
                continue
            snapshot = snapshots.get(symbol) or {}
            bid, ask, bid_size, ask_size = self._quote_fields(snapshot)
            expiration_raw = raw.get("expiration_date")
            try:
                expiration = date.fromisoformat(str(expiration_raw))
            except (TypeError, ValueError):
                continue
            candidates.append(
                OptionContractCandidate(
                    symbol=symbol,
                    underlying_symbol=str(raw.get("underlying_symbol") or ticker),
                    option_type=str(raw.get("type") or option_type).lower(),
                    strike_price=float(raw.get("strike_price") or 0),
                    expiration_date=expiration,
                    tradable=bool(raw.get("tradable", True)) and str(raw.get("status") or "active") == "active",
                    bid_price=bid,
                    ask_price=ask,
                    bid_size=bid_size,
                    ask_size=ask_size,
                    delta=self._delta(snapshot),
                )
            )
        return candidates

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
