"""SIGNAL K1 — versioned, validated domain records (Python standard library only).

All monetary/quantity values are decimal *strings* in JSON, never binary floats.
All temporal instants MUST be timezone-aware ISO 8601 timestamps.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any
import re


class ContractError(ValueError):
    def __init__(self, code: str, detail: str):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def require_str(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError("MISSING_FIELD", f"{field_name} must be a nonempty string")
    return value


def instant(value: str, name: str = "timestamp") -> datetime:
    require_str(value, name)
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError("INVALID_TIME", f"{name} is not ISO8601: {value}") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ContractError("NAIVE_TIME", f"{name} must specify a timezone: {value}")
    return dt


def number(value: str, name: str = "value") -> Decimal:
    if not isinstance(value, str):
        raise ContractError("DECIMAL_AS_STRING_REQUIRED", f"{name} must be a string")
    try:
        result = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise ContractError("INVALID_DECIMAL", f"{name}={value!r}") from exc
    if not result.is_finite():
        raise ContractError("NONFINITE_VALUE", f"{name}={value!r}")
    return result


def required_list(value: object, name: str, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not value and not allow_empty) or any(not isinstance(v, str) or not v for v in value):
        raise ContractError("INVALID_LIST", f"{name} must be a list of nonempty strings")
    if len(value) != len(set(value)):
        raise ContractError("DUPLICATE_REFERENCE", f"{name} contains duplicated identifiers")
    return value


@dataclass(frozen=True, slots=True)
class SourceSnapshot:
    snapshot_id: str
    source_id: str
    source_uri: str
    published_at: str
    retrieved_at: str
    vintage_id: str
    payload_sha256: str
    rights_scope: str
    source_type: str
    schema_version: str = "1.0"

    def __post_init__(self):
        for item in ("snapshot_id", "source_id", "source_uri", "vintage_id", "rights_scope", "source_type"):
            require_str(getattr(self, item), item)
        if not re.fullmatch(r"[0-9a-f]{64}", self.payload_sha256):
            raise ContractError("INVALID_HASH", "snapshot requires full lowercase SHA-256")
        if instant(self.retrieved_at, "retrieved_at") < instant(self.published_at, "published_at"):
            raise ContractError("TIME_ORDER", "retrieved_at cannot predate published_at")
        if self.schema_version != "1.0":
            raise ContractError("SCHEMA_VERSION", "unsupported SourceSnapshot schema")


@dataclass(frozen=True, slots=True)
class Observation:
    observation_id: str
    series_id: str
    value: str
    unit: str
    period: str
    frequency: str
    available_at: str
    data_status: str
    snapshot_id: str
    vintage_id: str
    commodity: str
    geography: str
    measurement_basis: str
    schema_version: str = "1.0"

    def __post_init__(self):
        for key in ("observation_id", "series_id", "unit", "period", "frequency", "data_status", "snapshot_id", "vintage_id", "commodity", "geography", "measurement_basis"):
            require_str(getattr(self, key), key)
        number(self.value)
        instant(self.available_at, "available_at")
        if self.frequency not in {"day", "week", "month", "quarter", "year", "marketing_year"}:
            raise ContractError("INVALID_FREQUENCY", self.frequency)
        patterns = {
            "day": r"\d{4}-\d{2}-\d{2}",
            "week": r"\d{4}-W\d{2}",
            "month": r"\d{4}-(?:0[1-9]|1[0-2])",
            "quarter": r"\d{4}-Q[1-4]",
            "year": r"\d{4}",
            "marketing_year": r"MY\d{4}/\d{2}",
        }
        if not re.fullmatch(patterns[self.frequency], self.period):
            raise ContractError("PERIOD_FORMAT_MISMATCH", f"{self.period} cannot be {self.frequency}")
        if self.frequency == "marketing_year":
            start = int(self.period[2:6])
            end = int(self.period[7:9])
            if (start + 1) % 100 != end:
                raise ContractError("PERIOD_FORMAT_MISMATCH", "marketing year must advance one year")
        if self.frequency == "day":
            try:
                datetime.strptime(self.period, "%Y-%m-%d")
            except ValueError as exc:
                raise ContractError("PERIOD_FORMAT_MISMATCH", "invalid calendar day") from exc
        if self.data_status not in {"observed", "official_estimate", "revised_estimate", "synthetic_fixture"}:
            raise ContractError("INVALID_STATUS", self.data_status)
        if self.schema_version != "1.0":
            raise ContractError("SCHEMA_VERSION", "unsupported Observation schema")


@dataclass(frozen=True, slots=True)
class EventSignal:
    event_id: str
    detected_at: str
    event_type: str
    observation_ids: list[str]
    candidate_causes: list[str]
    causal_status: str = "unverified_candidates"
    schema_version: str = "1.0"

    def __post_init__(self):
        require_str(self.event_id, "event_id")
        require_str(self.event_type, "event_type")
        instant(self.detected_at, "detected_at")
        required_list(self.observation_ids, "observation_ids")
        required_list(self.candidate_causes, "candidate_causes", allow_empty=True)
        if self.causal_status != "unverified_candidates":
            raise ContractError("CAUSAL_OVERCLAIM", "K1 events cannot certify a reverse causal explanation")


@dataclass(frozen=True, slots=True)
class CausalLink:
    link_id: str
    from_variable: str
    to_variable: str
    relation_type: str
    lag_description: str
    scope: str
    evidence_status: str
    supporting_evidence_ids: list[str] = field(default_factory=list)
    identification_method: str = ""
    schema_version: str = "1.0"

    def __post_init__(self):
        for key in ("link_id", "from_variable", "to_variable", "relation_type", "lag_description", "scope", "evidence_status"):
            require_str(getattr(self, key), key)
        allowed = {
            "accounting_identity": "definition",
            "empirical_association": "correlational",
            "causal_hypothesis": "hypothesis",
            "causal_evidence": "causally_identified",
        }
        if self.relation_type not in allowed or self.evidence_status != allowed[self.relation_type]:
            raise ContractError("CAUSAL_STATUS_MISMATCH", "relationship and evidence status conflict")
        required_list(self.supporting_evidence_ids, "supporting_evidence_ids", allow_empty=True)
        if self.relation_type == "causal_evidence" and (not self.supporting_evidence_ids or not self.identification_method.strip()):
            raise ContractError("CAUSAL_OVERCLAIM", "causal evidence needs cited identification method; price move alone is insufficient")
        if self.relation_type == "causal_hypothesis" and not self.supporting_evidence_ids:
            # A hypothesis can remain a candidate; its evidential state remains explicit.
            pass


@dataclass(frozen=True, slots=True)
class ForecastRun:
    forecast_id: str
    as_of: str
    target_series_id: str
    target_period: str
    horizon_days: int
    model_version: str
    input_ids: list[str]
    p10: str
    p50: str
    p90: str
    baseline: str
    data_status: str = "synthetic_fixture"
    schema_version: str = "1.0"

    def __post_init__(self):
        for key in ("forecast_id", "target_series_id", "target_period", "model_version", "baseline"):
            require_str(getattr(self, key), key)
        instant(self.as_of, "as_of")
        if not isinstance(self.horizon_days, int) or isinstance(self.horizon_days, bool) or self.horizon_days <= 0:
            raise ContractError("INVALID_HORIZON", "horizon_days must be positive integer")
        required_list(self.input_ids, "input_ids")
        if not number(self.p10, "p10") <= number(self.p50, "p50") <= number(self.p90, "p90"):
            raise ContractError("INVALID_QUANTILES", "require p10 <= p50 <= p90")
        if self.data_status != "synthetic_fixture":
            raise ContractError("NO_REAL_FORECAST_IN_K1", "K1 is contract QA, not a production forecast")


@dataclass(frozen=True, slots=True)
class InvestmentHypothesis:
    hypothesis_id: str
    created_at: str
    mechanism: str
    asset_scope: str
    time_horizon: str
    supporting_evidence: list[str]
    counter_hypotheses: list[str]
    invalidation: str
    status: str = "unverified_research_only"
    schema_version: str = "1.0"

    def __post_init__(self):
        for key in ("hypothesis_id", "mechanism", "asset_scope", "time_horizon", "invalidation"):
            require_str(getattr(self, key), key)
        instant(self.created_at, "created_at")
        required_list(self.supporting_evidence, "supporting_evidence")
        required_list(self.counter_hypotheses, "counter_hypotheses")
        if self.status != "unverified_research_only":
            raise ContractError("NOT_APPROVED", "K1 hypothesis cannot be represented as verified or investable")


@dataclass(frozen=True, slots=True)
class DecisionRecord:
    decision_id: str
    hypothesis_id: str
    as_of: str
    instrument: str
    price_as_of: str
    reference_price: str
    quote_currency: str
    strategy: str
    costs: str
    risk_limit: str
    paper_only: bool = True
    schema_version: str = "1.0"

    def __post_init__(self):
        for key in ("decision_id", "hypothesis_id", "instrument", "quote_currency", "strategy", "risk_limit"):
            require_str(getattr(self, key), key)
        instant(self.as_of, "as_of")
        if instant(self.price_as_of, "price_as_of") > instant(self.as_of, "as_of"):
            raise ContractError("FUTURE_PRICE", "price cannot be known after decision as_of")
        number(self.reference_price, "reference_price")
        number(self.costs, "costs")
        if self.paper_only is not True:
            raise ContractError("NO_LIVE_TRADING", "K1 is paper-only")


def to_record(instance: Any) -> dict[str, Any]:
    return asdict(instance)
