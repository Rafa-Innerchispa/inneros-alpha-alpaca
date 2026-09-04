from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .models import ContractSelection, MarketSnapshot, OptionContractCandidate, TradeIntent


@dataclass(frozen=True)
class ContractPolicy:
    min_dte: int = 14
    max_dte: int = 45
    default_target_dte: int = 30
    max_spread_pct: float = 0.15
    target_abs_delta: float = 0.35
    min_strike_ratio: float = 0.90
    max_strike_ratio: float = 1.10


class DeterministicContractSelector:
    """Selects an option contract without delegating symbol choice to the LLM."""

    def __init__(self, policy: ContractPolicy | None = None) -> None:
        self.policy = policy or ContractPolicy()

    @staticmethod
    def _spread_pct(contract: OptionContractCandidate) -> float | None:
        if contract.bid_price <= 0 or contract.ask_price <= 0:
            return None
        midpoint = (contract.bid_price + contract.ask_price) / 2
        if midpoint <= 0:
            return None
        return (contract.ask_price - contract.bid_price) / midpoint

    def select(
        self,
        *,
        snapshot: MarketSnapshot,
        intent: TradeIntent,
        candidates: list[OptionContractCandidate],
        today: date | None = None,
    ) -> ContractSelection:
        scanned = len(candidates)
        counts = {
            "raw": scanned,
            "tradable_type": 0,
            "dte": 0,
            "strike": 0,
            "spread": 0,
            "eligible": 0,
        }
        if intent.correlation_id != snapshot.correlation_id:
            return ContractSelection(
                status="BLOCKED",
                reason="Correlation mismatch between market snapshot and trade intent",
                candidates_scanned=scanned,
                filter_counts=counts,
                correlation_id=intent.correlation_id,
            )
        if intent.bias == "NEUTRAL" or intent.strategy == "no_trade":
            return ContractSelection(
                status="NO_TRADE",
                reason="Neutral/no-trade intent requires no contract selection",
                candidates_scanned=scanned,
                filter_counts=counts,
                correlation_id=intent.correlation_id,
            )

        option_type = "call" if intent.bias == "BULLISH" else "put"
        target_dte = intent.dte_target or self.policy.default_target_dte
        target_dte = min(max(target_dte, self.policy.min_dte), self.policy.max_dte)
        today = today or date.today()
        min_strike = snapshot.price * self.policy.min_strike_ratio
        max_strike = snapshot.price * self.policy.max_strike_ratio

        scored: list[tuple[tuple[float, float, float, float], OptionContractCandidate, float]] = []
        for contract in candidates:
            if not contract.tradable:
                continue
            if contract.underlying_symbol != snapshot.ticker:
                continue
            if contract.option_type != option_type:
                continue
            counts["tradable_type"] += 1

            dte = (contract.expiration_date - today).days
            if dte < self.policy.min_dte or dte > self.policy.max_dte:
                continue
            counts["dte"] += 1

            if not (min_strike <= contract.strike_price <= max_strike):
                continue
            counts["strike"] += 1

            spread = self._spread_pct(contract)
            if spread is None or spread > self.policy.max_spread_pct:
                continue
            counts["spread"] += 1

            dte_distance = abs(dte - target_dte)
            strike_distance = abs(contract.strike_price - snapshot.price) / max(snapshot.price, 1)
            if contract.delta is None:
                delta_distance = 1.0
            else:
                delta_distance = abs(abs(contract.delta) - self.policy.target_abs_delta)
            liquidity_tiebreak = -float(contract.bid_size + contract.ask_size)
            score = (float(dte_distance), delta_distance, spread + strike_distance, liquidity_tiebreak)
            scored.append((score, contract, spread))

        counts["eligible"] = len(scored)
        if not scored:
            return ContractSelection(
                status="NO_TRADE",
                reason="No tradable contract passed DTE, strike, quote, and spread gates",
                candidates_scanned=scanned,
                candidates_eligible=0,
                filter_counts=counts,
                correlation_id=intent.correlation_id,
            )

        scored.sort(key=lambda item: item[0])
        _, selected, spread = scored[0]
        estimated_max_loss = selected.ask_price * 100 * intent.quantity
        return ContractSelection(
            status="SELECTED",
            contract=selected,
            reason="Deterministic contract policy selected the best eligible contract",
            estimated_max_loss=estimated_max_loss,
            spread_pct=spread,
            candidates_scanned=scanned,
            candidates_eligible=len(scored),
            filter_counts=counts,
            correlation_id=intent.correlation_id,
        )

    @staticmethod
    def apply_to_intent(intent: TradeIntent, selection: ContractSelection) -> TradeIntent:
        if selection.status != "SELECTED" or selection.contract is None:
            return intent
        contract = selection.contract
        updated = intent.model_copy(deep=True)
        updated.option_symbol = contract.symbol
        updated.expiry = contract.expiration_date.isoformat()
        updated.dte_target = (contract.expiration_date - date.today()).days
        updated.delta_target = contract.delta
        updated.estimated_max_loss = selection.estimated_max_loss
        return updated
