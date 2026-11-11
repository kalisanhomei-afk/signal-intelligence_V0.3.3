"""Point-in-time data eligibility; timestamp policy is explicit."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from .contracts import ContractError, SourceSnapshot, Observation, ForecastRun, instant


@dataclass(frozen=True)
class TimePolicy:
    # In a system replay, data must have been retrieved by the system at as_of.
    # A public-information audit may relax this, but MUST be labelled as distinct.
    require_local_retrieval: bool = True


def validate_observation_provenance(obs: Observation, snapshot: SourceSnapshot) -> None:
    if obs.snapshot_id != snapshot.snapshot_id:
        raise ContractError("SNAPSHOT_MISMATCH", f"{obs.observation_id} references another snapshot")
    if obs.vintage_id != snapshot.vintage_id:
        raise ContractError("VINTAGE_MISMATCH", f"{obs.observation_id} mismatches source vintage")
    if instant(obs.available_at) < instant(snapshot.published_at):
        raise ContractError("AVAILABLE_BEFORE_PUBLICATION", obs.observation_id)
    if instant(obs.available_at) > instant(snapshot.retrieved_at):
        raise ContractError("UNAVAILABLE_AT_RETRIEVAL", obs.observation_id)


def check_asof(obs: Observation, snapshot: SourceSnapshot, as_of: str, *, policy: TimePolicy = TimePolicy()) -> None:
    validate_observation_provenance(obs, snapshot)
    cutoff = instant(as_of, "as_of")
    if instant(snapshot.published_at) > cutoff or instant(obs.available_at) > cutoff:
        raise ContractError("FUTURE_DATA", f"{obs.observation_id} was not public at {as_of}")
    if policy.require_local_retrieval and instant(snapshot.retrieved_at) > cutoff:
        raise ContractError("NOT_YET_RETRIEVED", f"{obs.observation_id} was not acquired by SIGNAL at {as_of}")


def validate_forecast_inputs(
    run: ForecastRun,
    observations: dict[str, Observation],
    snapshots: dict[str, SourceSnapshot],
    *,
    policy: TimePolicy = TimePolicy(),
) -> list[Observation]:
    selected = []
    for obs_id in run.input_ids:
        obs = observations.get(obs_id)
        if obs is None:
            raise ContractError("MISSING_INPUT", obs_id)
        snapshot = snapshots.get(obs.snapshot_id)
        if snapshot is None:
            raise ContractError("MISSING_SOURCE", obs.snapshot_id)
        check_asof(obs, snapshot, run.as_of, policy=policy)
        selected.append(obs)
    return selected


def select_asof(
    observations: list[Observation],
    snapshots: dict[str, SourceSnapshot],
    as_of: str,
    *,
    policy: TimePolicy = TimePolicy(),
) -> dict[str, Observation]:
    """Pick latest *eligible* vintage for each semantic series/period/scope.

    Never mix components across periods/scopes. A revision that is public but
    not yet retrieved cannot overwrite the earlier system-known snapshot.
    """
    selected: dict[str, Observation] = {}
    rank: dict[str, tuple[datetime, datetime, str]] = {}
    identities: dict[str, str] = {}
    for obs in observations:
        snap = snapshots.get(obs.snapshot_id)
        if snap is None:
            raise ContractError("MISSING_SOURCE", obs.snapshot_id)
        try:
            check_asof(obs, snap, as_of, policy=policy)
        except ContractError as exc:
            if exc.code in {"FUTURE_DATA", "NOT_YET_RETRIEVED"}:
                continue
            raise
        # Composite identity prevents different frequency, scope or units
        # being mistaken for successive revisions of a single series.
        series_key = "|".join((obs.series_id, obs.period, obs.frequency, obs.geography, obs.commodity, obs.measurement_basis, obs.unit))
        if obs.series_id in identities and identities[obs.series_id] != series_key:
            raise ContractError("AMBIGUOUS_SERIES_SCOPE", f"{obs.series_id} has multiple periods/units/scopes; filter before replay")
        identities[obs.series_id] = series_key
        current_rank = (instant(obs.available_at), instant(snap.published_at), obs.snapshot_id)
        if series_key not in rank or current_rank > rank[series_key]:
            rank[series_key] = current_rank
            selected[obs.series_id] = obs
    return selected
