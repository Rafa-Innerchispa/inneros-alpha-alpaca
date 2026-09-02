from __future__ import annotations

import json
import os
import re

import httpx

from .models import MarketSnapshot, TradeIntent


DEFAULT_MODEL = "QuantTrio/Qwen3-Coder-30B-A3B-Instruct-AWQ"


class LocalReasoningClient:
    """Local-first strategy proposer for the AMD 1.5 OpenAI-compatible vLLM endpoint.

    Failure is intentionally conservative: malformed/unreachable model output becomes
    a NEUTRAL no-trade intent. This class never has broker credentials and cannot place orders.
    """

    def __init__(self) -> None:
        self.base_url = os.getenv("INNEROS_REASONING_URL", "http://127.0.0.1:8000/v1").rstrip("/")
        self.model = os.getenv("INNEROS_REASONING_MODEL", DEFAULT_MODEL)
        self.timeout_seconds = float(os.getenv("INNEROS_REASONING_TIMEOUT", "25"))

    def status(self) -> dict:
        """Return redacted readiness for the local reasoning runtime."""
        status = {
            "provider": "local-amd-5",
            "runtime": "vllm",
            "model": self.model,
            "reachable": False,
            "model_available": False,
        }
        try:
            with httpx.Client(timeout=min(self.timeout_seconds, 3.0)) as client:
                response = client.get(f"{self.base_url}/models")
                response.raise_for_status()
                payload = response.json()
            models = [str(item.get("id") or "") for item in payload.get("data", [])]
            status["reachable"] = True
            status["model_available"] = self.model in models
        except Exception as exc:
            status["error"] = type(exc).__name__
        return status

    def _no_trade(self, snapshot: MarketSnapshot, reason: str) -> TradeIntent:
        return TradeIntent(
            ticker=snapshot.ticker,
            bias="NEUTRAL",
            confidence=0,
            strategy="no_trade",
            rationale=reason,
            estimated_max_loss=0,
            correlation_id=snapshot.correlation_id,
        )

    @staticmethod
    def _extract_json(text: str) -> dict:
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"\s*```$", "", text)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, flags=re.DOTALL)
            if not match:
                raise
            return json.loads(match.group(0))

    def propose(self, snapshot: MarketSnapshot) -> TradeIntent:
        system = (
            "You are the local Strategy Agent inside InnerOS Alpha. "
            "You may propose only a PAPER-trading TradeIntent. You cannot approve risk or execute. "
            "Return exactly one JSON object and no commentary. If evidence is insufficient, return "
            "bias=NEUTRAL, strategy=no_trade, confidence=0, estimated_max_loss=0. "
            "Never invent an option_symbol. Contract selection is deterministic code outside the LLM."
        )
        schema = {
            "ticker": snapshot.ticker,
            "bias": "BULLISH|BEARISH|NEUTRAL",
            "confidence": "0..1",
            "strategy": "long_call|long_put|defined_risk_spread|no_trade",
            "expiry": None,
            "dte_target": None,
            "delta_target": None,
            "rationale": "short evidence-based reason",
            "estimated_max_loss": 0,
            "option_symbol": None,
            "quantity": 1,
            "correlation_id": snapshot.correlation_id,
        }
        user = (
            "Produce a TradeIntent from this market snapshot. Hard limits: initial DTE 14-45 days; "
            "risk approval and contract selection are external and deterministic; do not bypass them.\n"
            f"Expected JSON shape: {json.dumps(schema)}\n"
            f"Snapshot: {snapshot.model_dump_json()}"
        )
        payload = {
            "model": self.model,
            "temperature": 0.1,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(f"{self.base_url}/chat/completions", json=payload)
                response.raise_for_status()
                data = response.json()
            text = data["choices"][0]["message"]["content"]
            raw = self._extract_json(text)
            raw["ticker"] = snapshot.ticker
            raw["correlation_id"] = snapshot.correlation_id
            raw["option_symbol"] = None
            return TradeIntent.model_validate(raw)
        except Exception as exc:  # fail closed into NO_TRADE
            return self._no_trade(snapshot, f"Local reasoning unavailable or invalid: {type(exc).__name__}")
