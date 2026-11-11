"""K2 dual engines: forward counterfactual and reverse diagnostic candidates.

Strict separation:
* accounting implication: calculated from K1 stocks-and-flows identity
* observed revision: later, as-of-valid snapshot compared with earlier snapshot
* candidate upstream cause: UNVERIFIED until additional independent evidence

Only synthetic fixture data are permitted in this prototype.  No prediction of
market prices, causal identification, or calibrated forecast is claimed.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from decimal import Decimal
from typing import Mapping, Sequence

from research_core.asof_guard import select_asof
from research_core.contracts import (
    ContractError, Observation, SourceSnapshot, number, instant,
    EventSignal, CausalLink
)
from research_core.stockflow import REQUIRED, check_balance

FLOW_SIGN = {"beginning_stocks": 1, "production": 1, "imports": 1,
             "domestic_use": -1, "exports": -1}
DRIVERS = tuple(FLOW_SIGN)
IDENTITY = "ending_stocks = beginning_stocks + production + imports - domestic_use - exports"
DATA_TYPE = "SYNTHETIC_ONLY_NOT_USDA"


def fmt(value: Decimal) -> str:
    """Finite decimal string; no binary floating-point artifacts."""
    if not value.is_finite():
        raise ContractError("NONFINITE_VALUE", "K2 numeric output must be finite")
    s = format(value, "f")
    return s.rstrip("0").rstrip(".") if "." in s else s


@dataclass(frozen=True)
class AsOfState:
    as_of: str
    values: dict[str, str]
    observation_ids: dict[str, str]
    snapshot_ids: dict[str, str]
    unit: str
    period: str
    frequency: str
    commodity: str
    geography: str
    measurement_basis: str
    vintage_id: str
    ending_stocks: str

    def to_dict(self) -> dict:
        return asdict(self)


def state_at(observations: Sequence[Observation], snapshots: Mapping[str, SourceSnapshot], as_of: str) -> AsOfState:
    """Construct one K1-checked, balanced, time-eligible synthetic data state."""
    instant(as_of, "as_of")
    if not observations or any(x.data_status != "synthetic_fixture" for x in observations):
        raise ContractError("K2_SYNTHETIC_ONLY", "K2 pilot accepts synthetic fixtures only")
    if not snapshots or any(x.source_type != "synthetic_fixture" for x in snapshots.values()):
        raise ContractError("K2_SYNTHETIC_ONLY", "K2 pilot accepts synthetic snapshots only")
    selected = select_asof(list(observations), dict(snapshots), as_of)
    if set(selected) != set(REQUIRED):
        raise ContractError("INCOMPLETE_STOCKFLOW", "requires exactly six comparable series: " + ",".join(sorted(selected)))
    balance = check_balance(list(selected.values()))
    if not balance.balanced:
        raise ContractError("UNBALANCED_INPUT", balance.discrepancy)
    first = selected["ending_stocks"]
    return AsOfState(
        as_of=as_of, values={s: selected[s].value for s in REQUIRED},
        observation_ids={s: selected[s].observation_id for s in REQUIRED},
        snapshot_ids={s: selected[s].snapshot_id for s in REQUIRED},
        unit=first.unit, period=first.period, frequency=first.frequency,
        commodity=first.commodity, geography=first.geography,
        measurement_basis=first.measurement_basis, vintage_id=first.vintage_id,
        ending_stocks=balance.reported_ending,
    )


@dataclass(frozen=True)
class ScenarioSpec:
    scenario_id: str
    as_of: str
    shocks: dict[str, str]
    rationale: str
    scenario_kind: str = "USER_DECLARED_SYNTHETIC_WHAT_IF"

    def __post_init__(self):
        if not self.scenario_id.strip() or not self.rationale.strip():
            raise ContractError("INVALID_SCENARIO", "scenario id and reason required")
        instant(self.as_of)
        if self.scenario_kind != "USER_DECLARED_SYNTHETIC_WHAT_IF":
            raise ContractError("UNVERIFIED_FORECAST", "K2 scenario is not a calibrated probabilistic forecast")
        if not isinstance(self.shocks, dict) or not self.shocks:
            raise ContractError("INVALID_SCENARIO", "at least one shock must be provided")
        if set(self.shocks) - set(DRIVERS):
            raise ContractError("SHOCK_TO_TARGET_FORBIDDEN", "only five stockflow drivers may be shocked; ending_stocks is computed")
        for key, val in self.shocks.items():
            number(val, f"shock:{key}")


def forward_scenario(state: AsOfState, spec: ScenarioSpec) -> dict:
    if instant(state.as_of) != instant(spec.as_of):
        raise ContractError("ASOF_MISMATCH", "scenario as_of must equal source snapshot time")
    base = {k: number(state.values[k]) for k in REQUIRED}
    new = {k: base[k] for k in DRIVERS}
    for series, shock in spec.shocks.items():
        new[series] += number(shock)
    if any(v < 0 for v in new.values()):
        raise ContractError("NEGATIVE_SCENARIO_INPUT", "a scenario component cannot become negative")
    projected_ending = sum((Decimal(FLOW_SIGN[k]) * new[k] for k in DRIVERS), Decimal(0))
    if projected_ending < 0:
        raise ContractError("NEGATIVE_PROJECTED_STOCK", "counterfactual stocks cannot be negative in simple K2 pilot")
    delta_ending = projected_ending - base["ending_stocks"]
    contributions = {k: fmt(Decimal(FLOW_SIGN[k]) * number(spec.shocks.get(k, "0"))) for k in DRIVERS}
    if sum((number(c) for c in contributions.values()), Decimal(0)) != delta_ending:
        raise ContractError("IDENTITY_FAILURE", "sum of contributions differs from projected stock delta")
    return {
        "scenario_id": spec.scenario_id, "as_of": spec.as_of,
        "data_type": DATA_TYPE, "scenario_kind": spec.scenario_kind,
        "forecast_claim": False, "probabilities_calibrated": False,
        "rationale": spec.rationale, "identity": IDENTITY,
        "base_vintage": state.vintage_id, "base_observation_ids": state.observation_ids,
        "unit": state.unit, "period": state.period, "commodity": state.commodity,
        "base_components": state.values, "shocks": spec.shocks,
        "counterfactual_components": {k: fmt(v) for k, v in new.items()},
        "base_ending_stocks": state.ending_stocks,
        "counterfactual_ending_stocks": fmt(projected_ending),
        "delta_ending_stocks": fmt(delta_ending),
        "accounting_contributions": contributions,
        "interpretation": "Accounting what-if only. The shock is user-declared; not an estimated real-world cause or investment signal.",
    }


def _compatible(before: AsOfState, after: AsOfState) -> None:
    for field in ("unit", "period", "frequency", "commodity", "geography", "measurement_basis"):
        if getattr(before, field) != getattr(after, field):
            raise ContractError("DIFFERENT_SCOPE", f"cannot compare {field} across states")
    if instant(after.as_of) <= instant(before.as_of):
        raise ContractError("INVALID_COMPARISON_ORDER", "later as_of must be strictly after earlier as_of")
    if before.vintage_id == after.vintage_id:
        raise ContractError("NO_NEW_VINTAGE", "revision comparison needs a new eligible vintage")


def reverse_diagnostic(before: AsOfState, after: AsOfState) -> dict:
    """Account for observed revision; DO NOT invert an association to causal proof."""
    _compatible(before, after)
    changes = {k: number(after.values[k]) - number(before.values[k]) for k in REQUIRED}
    accounting = {k: Decimal(FLOW_SIGN[k]) * changes[k] for k in DRIVERS}
    observed_stock_change = changes["ending_stocks"]
    if sum(accounting.values(), Decimal(0)) != observed_stock_change:
        raise ContractError("REVISION_IDENTITY_FAILURE", "stocks revision not explained by matched stockflow components")
    contributors = [
        {"series_id": k, "change": fmt(changes[k]),
         "accounting_contribution_to_ending_stocks": fmt(accounting[k]),
         "previous_observation_id": before.observation_ids[k],
         "current_observation_id": after.observation_ids[k],
         "explanation_status": "OBSERVED_ACCOUNTING_CONTRIBUTION_NOT_CAUSAL_IDENTIFICATION"}
        for k in DRIVERS if changes[k] != 0
    ]
    # Explicit competing upstream stories: not identified from the inventory identity.
    # A source observation of production change is not evidence for weather vs acreage.
    candidates = [
        {"candidate_id": "yield_revision", "proposed_mechanism": "單產預估調整使產量修訂",
         "supporting_observation_ids": [], "status": "UNTESTED_CANDIDATE",
         "test_needed": "同一時點可得的單產預估、氣候及作物生長資料"},
        {"candidate_id": "area_revision", "proposed_mechanism": "面積修訂使產量預估改變",
         "supporting_observation_ids": [], "status": "UNTESTED_CANDIDATE",
         "test_needed": "同一時點可得的種植與收穫面積修訂資料"},
        {"candidate_id": "method_revision", "proposed_mechanism": "統計或估計方法修訂",
         "supporting_observation_ids": [], "status": "UNTESTED_CANDIDATE",
         "test_needed": "機構發布的修訂說明或方法學變動"},
    ]
    event = EventSignal(
        event_id=f"K2-REVISION-{before.vintage_id}-{after.vintage_id}",
        detected_at=after.as_of, event_type="synthetic_stockflow_revision",
        observation_ids=[after.observation_ids["ending_stocks"]],
        candidate_causes=[c["candidate_id"] for c in candidates],
    )
    causal_hypotheses = [
        asdict(CausalLink(link_id=f"K2-{c['candidate_id']}", from_variable=c["candidate_id"],
                          to_variable="production", relation_type="causal_hypothesis",
                          lag_description="unknown; requires domain study",
                          scope="synthetic US corn marketing-year fixture",
                          evidence_status="hypothesis", supporting_evidence_ids=[]))
        for c in candidates
    ]
    return {
        "data_type": DATA_TYPE, "diagnostic_mode": "REVISION_ACCOUNTING_NOT_CAUSAL_IDENTIFICATION",
        "before_as_of": before.as_of, "after_as_of": after.as_of,
        "before_vintage": before.vintage_id, "after_vintage": after.vintage_id,
        "period": after.period, "unit": after.unit, "identity": IDENTITY,
        "observed_ending_stock_change": fmt(observed_stock_change),
        "accounting_contributors": contributors, "upstream_candidate_causes": candidates,
        "k1_event_signal": asdict(event), "k1_causal_hypotheses": causal_hypotheses,
        "causality_confirmed": False,
        "warning": "The stockflow identity explains how the bookkeeping changed, not why it changed. No causal reversal is proven.",
    }


def close_loop(forward: dict, reverse: dict) -> dict:
    """At the later as_of, compare earlier declared synthetic scenario to observed revision."""
    if forward.get("data_type") != DATA_TYPE or reverse.get("data_type") != DATA_TYPE:
        raise ContractError("MIXED_DATA_TYPE", "K2 loop only accepts synthetic results")
    if instant(forward["as_of"]) != instant(reverse["before_as_of"]):
        raise ContractError("ASOF_MISMATCH", "scenario must have been defined at the earlier observation time")
    if forward["base_vintage"] != reverse["before_vintage"]:
        raise ContractError("VINTAGE_MISMATCH", "comparison baseline must be same original source vintage")
    if forward["unit"] != reverse["unit"] or forward["period"] != reverse["period"]:
        raise ContractError("DIFFERENT_SCOPE", "cannot compare unrelated quantities")
    scenario_delta = number(forward["delta_ending_stocks"])
    observed_delta = number(reverse["observed_ending_stock_change"])
    return {
        "data_type": DATA_TYPE,
        "evaluation_at": reverse["after_as_of"],
        "scenario_frozen_as_of": forward["as_of"],
        "scenario_id": forward["scenario_id"],
        "scenario_delta": fmt(scenario_delta), "observed_revision_delta": fmt(observed_delta),
        "revision_delta_residual_observed_minus_scenario": fmt(observed_delta - scenario_delta),
        "causal_validation": "NOT_ESTABLISHED",
        "predictive_edge": "NOT_TESTED_SINGLE_SYNTHETIC_CASE",
        "investment_signal": False,
        "next_research": [
            "Collect actual vintage-stamped crop-yield and harvested-area observations at each prediction cutoff",
            "Distinguish official forecast revisions from harvest realizations and market expectations",
            "Use many strictly out-of-sample periods before claiming forecast skill",
        ],
    }
