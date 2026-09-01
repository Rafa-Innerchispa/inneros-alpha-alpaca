from __future__ import annotations

from typing import Any

import httpx

from .config import Settings
from .contracts import ExecutionResult, RiskDecision, TerminalState, TradeIntent


class AlpacaPaperAdapter:
    def __init__(self, settings: Settings):
        self.settings = settings

    def ready(self) -> dict[str, Any]:
        headers = self.settings.alpaca_headers()
        return {
            "ok": self.settings.alpaca_paper and bool(headers),
            "paper_only": self.settings.alpaca_paper,
            "api_base": self.settings.normalized_api_base,
            "credentials_present": bool(headers),
        }

    async def submit_order(self, intent: TradeIntent, risk: RiskDecision) -> ExecutionResult:
        if not risk.allowed:
            return ExecutionResult(
                state=TerminalState.BLOCKED,
                intent=intent,
                risk=risk,
                evidence={"reason": "risk_blocked"},
            )
        if not self.settings.alpaca_paper:
            return ExecutionResult(
                state=TerminalState.BLOCKED,
                intent=intent,
                risk=risk,
                evidence={"reason": "live_trading_disabled"},
            )
        headers = self.settings.alpaca_headers()
        if not headers:
            return ExecutionResult(
                state=TerminalState.NO_TRADE,
                intent=intent,
                risk=risk,
                evidence={"reason": "alpaca_paper_credentials_missing"},
            )

        payload: dict[str, Any] = {
            "symbol": intent.symbol,
            "qty": str(intent.qty),
            "side": intent.side.value,
            "type": intent.order_type.value,
            "time_in_force": intent.time_in_force.value,
        }
        if intent.limit_price:
            payload["limit_price"] = str(intent.limit_price)

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"{self.settings.normalized_api_base}/v2/orders",
                headers=headers,
                json=payload,
            )
        if response.status_code >= 400:
            return ExecutionResult(
                state=TerminalState.FAIL,
                intent=intent,
                risk=risk,
                source="ALPACA_PAPER",
                evidence={"status_code": response.status_code, "body": response.text[:1000]},
            )
        data = response.json()
        return ExecutionResult(
            state=TerminalState.PASS,
            intent=intent,
            risk=risk,
            source="ALPACA_PAPER",
            alpaca_order_id=str(data.get("id") or ""),
            evidence={"status_code": response.status_code, "paper_order": data},
        )
