"""Stock-flow identity and strict comparability checks (no silent repairs)."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from decimal import Decimal
from .contracts import ContractError, Observation, number

REQUIRED = ("beginning_stocks", "production", "imports", "domestic_use", "exports", "ending_stocks")


@dataclass(frozen=True)
class BalanceResult:
    calculated_ending: str
    reported_ending: str
    discrepancy: str
    tolerance: str
    balanced: bool
    unit: str
    period: str
    data_status: str

    def as_dict(self):
        return asdict(self)


def check_balance(observations: list[Observation], *, tolerance: str = "0") -> BalanceResult:
    tol = number(tolerance, "tolerance")
    if tol < 0:
        raise ContractError("INVALID_TOLERANCE", "tolerance cannot be negative")
    lookup: dict[str, Observation] = {}
    for obs in observations:
        if obs.series_id in lookup:
            raise ContractError("DUPLICATE_SERIES", obs.series_id)
        lookup[obs.series_id] = obs
    missing = [key for key in REQUIRED if key not in lookup]
    if missing:
        raise ContractError("MISSING_COMPONENT", ",".join(missing))
    parts = [lookup[key] for key in REQUIRED]
    # The component set must be a single snapshot/vintage and common scope.
    for key in ("unit", "period", "frequency", "geography", "commodity", "measurement_basis", "vintage_id", "snapshot_id", "data_status"):
        if len({getattr(p, key) for p in parts}) != 1:
            error = "UNIT_MISMATCH" if key == "unit" else "PERIOD_MISMATCH" if key in {"period", "frequency"} else "SCOPE_OR_VINTAGE_MISMATCH"
            raise ContractError(error, f"components have inconsistent {key}")
    values = {key: number(lookup[key].value) for key in REQUIRED}
    if any(val < 0 for val in values.values()):
        raise ContractError("NEGATIVE_STOCKFLOW", "this simplified corn balance needs nonnegative parts")
    expected = values["beginning_stocks"] + values["production"] + values["imports"] - values["domestic_use"] - values["exports"]
    difference = expected - values["ending_stocks"]
    return BalanceResult(
        calculated_ending=str(expected), reported_ending=str(values["ending_stocks"]), discrepancy=str(difference),
        tolerance=str(tol), balanced=abs(difference) <= tol, unit=parts[0].unit, period=parts[0].period,
        data_status=parts[0].data_status,
    )
