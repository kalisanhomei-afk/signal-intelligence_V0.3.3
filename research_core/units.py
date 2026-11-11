"""Exact scaling for like units; physical conversions require a documented factor."""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from .contracts import ContractError, number, require_str

SCALE_TO_BUSHELS = {
    "bushels": Decimal("1"),
    "thousand_bushels": Decimal("1000"),
    "million_bushels": Decimal("1000000"),
}


@dataclass(frozen=True)
class ConversionSpec:
    from_unit: str
    to_unit: str
    multiplier: str
    commodity: str
    source_reference: str

    def __post_init__(self):
        for key in ("from_unit", "to_unit", "commodity", "source_reference"):
            require_str(getattr(self, key), key)
        if number(self.multiplier, "multiplier") <= 0:
            raise ContractError("INVALID_CONVERSION", "multiplier must be positive")


def convert(value: str, from_unit: str, to_unit: str, *, commodity: str, conversion: ConversionSpec | None = None) -> str:
    v = number(value)
    require_str(commodity, "commodity")
    if from_unit == to_unit:
        return str(v)
    if from_unit in SCALE_TO_BUSHELS and to_unit in SCALE_TO_BUSHELS:
        return str(v * SCALE_TO_BUSHELS[from_unit] / SCALE_TO_BUSHELS[to_unit])
    if conversion is None:
        raise ContractError("INCOMPATIBLE_UNIT", f"{from_unit} -> {to_unit} needs documented commodity-specific conversion")
    if (conversion.from_unit, conversion.to_unit, conversion.commodity) != (from_unit, to_unit, commodity):
        raise ContractError("CONVERSION_SCOPE_MISMATCH", f"conversion does not apply to {commodity}")
    return str(v * number(conversion.multiplier))
