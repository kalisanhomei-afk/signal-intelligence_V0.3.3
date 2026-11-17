"""SIGNAL portfolio v1: strict, read-only contracts for research status and event cards.

This module never calls GitHub, scrapes sources, revises frozen forecasts, trains
models or executes trades. It validates a dated review snapshot, not live state.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
import json
import re

HERE = Path(__file__).resolve().parent
MANIFEST_PATH = HERE / "status_manifest.json"
REPO = "kalisanhomei-afk/signal-intelligence_V0.3.3"
SHA256 = re.compile(r"^[a-f0-9]{64}$")
GIT_SHA1 = re.compile(r"^[a-f0-9]{40}$")
UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")
SAFE_PATH = re.compile(r"^[a-zA-Z0-9._/-]+$")
UNITS = {"Bcf", "million_bushels"}
# Immutable 11/17 source commits continue to prove what was known BEFORE
# a research branch receives new post-event evidence. Never force old
# pre-release forecast URLs to follow the branch HEAD after an outcome commit.
FROZEN_SOURCE_COMMITS = {
    "H-CORN-001": "bdc68222f4b9ca7eba07b96205ac510c0d8bf345",
    "H-NG-001": "f613719479c9ede0add2e6ff0893c0fa1831c765",
}

CARD_KEYS = {
    "schema", "hypothesis_id", "title", "scope", "unit",
    "research_pr", "research_branch", "event_id", "target_period",
    "release_scheduled_utc", "forecast", "evidence", "market_consensus",
    "indicative_external_forecasts", "official_outcome", "score", "decision"
}
MANIFEST_KEYS = {
    "schema", "snapshot_date", "repository", "status_basis",
    "default_branch", "publication", "k38_main_registration", "prs",
    "layers", "research_cards", "last_known_test_evidence",
    "upcoming_checkpoints", "programme_gates"
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def utc(value: str) -> datetime:
    require(isinstance(value, str) and bool(UTC.fullmatch(value)), "INVALID_UTC_TIMESTAMP")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(parsed.utcoffset() is not None and parsed.utcoffset().total_seconds() == 0, "INVALID_UTC_OFFSET")
    return parsed


def number(value) -> Decimal:
    require(type(value) in (str, int, float), "INVALID_NUMERIC_VALUE")
    try:
        d = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("INVALID_NUMERIC_VALUE") from exc
    require(d.is_finite() and -1_000_000 <= d <= 1_000_000, "INVALID_NUMERIC_RANGE")
    return d


def hash_value(value, mode="sha256") -> bool:
    return isinstance(value, str) and bool(
        (SHA256 if mode == "sha256" else GIT_SHA1).fullmatch(value)
    )


def github_path(value) -> bool:
    return (isinstance(value, str) and len(value) <= 255 and
            bool(SAFE_PATH.fullmatch(value)) and
            ".." not in value.split("/") and not value.startswith("/") and
            "//" not in value)


def validate_manifest(m: dict):
    require(type(m) is dict and set(m) == MANIFEST_KEYS, "MANIFEST_CONTRACT_KEYS")
    require(m["schema"] == "signal-research-portfolio-v1", "MANIFEST_SCHEMA")
    date.fromisoformat(m["snapshot_date"])
    require(m["repository"] == REPO and m["default_branch"] == "main", "REPOSITORY_SCOPE_CHANGED")
    require("frozen snapshot" in m["status_basis"], "SNAPSHOT_NOT_DESCRIBED")
    p = m["publication"]
    require(p["research_branch_results_in_main"] is False, "IMPROPER_RESEARCH_PUBLICATION")
    require(p["current_public_site_revision_verified"] is False, "UNVERIFIED_DEPLOY_CLAIM")
    require(p["readme_and_index_version_labels_disagree"] is True, "VERSION_MISMATCH_NOT_DISCLOSED")
    k = m["k38_main_registration"]
    require(k["registration_pr"] == 20 and k["registration_pr_merged"] is True, "K38_REGISTRATION_MISSING")
    require(k["actual_capture_implementation_in_main"] is False, "K38_CAPTURE_PRODUCTION_MISREPRESENTED")
    require(k["auto_capture_schedule_enabled"] is False and
            k["default_branch_execution"] == "INTENTIONAL_FAIL_CLOSED", "K38_UNSAFE_OPERATION")
    prs = m["prs"]
    require(type(prs) is list and len(prs) == 4, "PR_SCOPE_MISMATCH")
    indexed = {p["number"]: p for p in prs}
    require(set(indexed) == {19, 20, 22, 23}, "PR_MISSING_OR_DUPLICATE")
    for ident in (19, 22, 23):
        q = indexed[ident]
        require(q["state"] == "open" and q["draft"] is True and q["merged"] is False,
                "RESEARCH_PR_NOT_DRAFT")
        require(q["base"] == "codex/k37-orchestration", "PR_RESEARCH_BASE_UNEXPECTED")
        if ident in (22, 23):
            require(hash_value(q.get("head_commit_sha"), "sha1"), "RESEARCH_COMMIT_ANCHOR_MISSING")
    require(indexed[20]["state"] == "closed" and indexed[20]["merged"] is True and
            indexed[20]["scope"] == "registration_only" and indexed[20]["base"] == "main",
            "PR20_EXAGGERATED")
    require(len(m["layers"]) == 6 and len({x["id"] for x in m["layers"]}) == 6,
            "SYSTEM_LAYERS_INCOMPLETE")
    for item in m["layers"]:
        require(item["status"] in {"PARTIAL_PROTOTYPE", "RESEARCH_VERIFIED",
                                  "NOT_VALIDATED", "NOT_IMPLEMENTED"}, "BAD_LAYER_STATUS")
    require(m["research_cards"] == [
        "research_overview/cards/H-CORN-001.json",
        "research_overview/cards/H-NG-001.json"
    ], "CARD_PATHS_CHANGED")
    ids = {e["pr"] for e in m["last_known_test_evidence"]}
    require(ids == {22, 23}, "MISSING_TEST_EVIDENCE")
    for result in m["last_known_test_evidence"]:
        require(type(result["passed"]) is int and result["passed"] > 0 and
                type(result["failed"]) is int and result["failed"] == 0, "MISLEADING_CI_COUNT")
        require(result["kind"] == "Engineering tests only", "TEST_NOT_ALPHA")
    for checkpoint in m["upcoming_checkpoints"]:
        require(datetime.fromisoformat(checkpoint["date_time_local"]).utcoffset().total_seconds() == 8*3600,
                "WRONG_CHECKPOINT_TZ")
    gates = m["programme_gates"]
    require(gates["model_v1"] == "ABSTAIN" and gates["alpha"] == "UNVERIFIED" and
            gates["trading"] == "NOT_AUTHORIZED", "UNSUPPORTED_READY_CLAIM")
    return m


def validate_card(c: dict, prs: dict):
    require(type(c) is dict and set(c) == CARD_KEYS, "CARD_CONTRACT_KEYS")
    require(c["schema"] == "signal-hypothesis-review-card-v1", "CARD_SCHEMA")
    require(c["hypothesis_id"] in {"H-CORN-001", "H-NG-001"}, "UNKNOWN_RESEARCH_CARD")
    require(c["unit"] in UNITS, "INVALID_UNIT")
    require(c["research_pr"] in prs and prs[c["research_pr"]]["draft"] is True,
            "NOT_ISOLATED_DRAFT_RESEARCH")
    require(c["research_branch"] == prs[c["research_pr"]]["branch"], "RESEARCH_BRANCH_MISMATCH")
    deadline = utc(c["release_scheduled_utc"])
    f = c["forecast"]
    require(f["frozen_before_event"] is True and type(f["value"]) in (int, float),
            "NO_FROZEN_V0")
    require(f["source_branch"] == c["research_branch"] and github_path(f["source_path"]),
            "FORECAST_SOURCE_PATH_MISMATCH")
    expected_forecast_files = {
        "H-CORN-001": "research_core/k4/cases/2026-12-10-forward-baseline-forecast.json",
        "H-NG-001": "research_core/k5/cases/2026-11-19-eia-frozen-v0-forecast.json",
    }
    require(f["source_path"] == expected_forecast_files[c["hypothesis_id"]],
            "FORECAST_ORIGINAL_PATH_MISMATCH")
    require(f.get("source_commit_ref") == FROZEN_SOURCE_COMMITS[c["hypothesis_id"]] and
            hash_value(f.get("source_git_blob_sha1"), "sha1"),
            "FORECAST_COMMIT_ANCHOR_MISMATCH")
    proof = f["frozen_proof"]
    require((proof["type"] == "git_blob_sha1" and hash_value(proof["value"], "sha1")) or
            (proof["type"] == "sha256_of_frozen_forecast_json" and hash_value(proof["value"])),
            "FORECAST_PROOF_MISSING")
    original = c["evidence"]
    require(original["prospective_raw_source_available"] is True, "NO_PRIOR_ORIGINAL_EVIDENCE")
    require(github_path(original["prospective_raw_source_path"]) and
            hash_value(original["prospective_raw_source_sha256"]), "PRIOR_ORIGINAL_HASH_MISSING")
    require(original.get("source_commit_ref") == FROZEN_SOURCE_COMMITS[c["hypothesis_id"]] and
            hash_value(original.get("source_git_blob_sha1"), "sha1"),
            "PRIOR_EVIDENCE_COMMIT_ANCHOR_MISMATCH")
    require(original["historical_predictor_pit_verified"] is False and
            original["prior_source_capture_utc_independently_attested"] is False,
            "SOURCE_PIT_PROMOTED_WITHOUT_PROOF")
    consensus = c["market_consensus"]
    require(consensus["status"] in {"NOT_VERIFIED", "VERIFIED_PRE_RELEASE"},
            "UNRECOGNIZED_CONSENSUS_STATUS")
    if consensus["status"] == "NOT_VERIFIED":
        require(consensus["value"] is None and consensus["pre_event_capture_utc"] is None and
                consensus["raw_sha256"] is None, "UNVERIFIED_CONSENSUS_MUST_BE_NULL")
    else:
        require(consensus["value"] is not None and number(consensus["value"]) >= 0 and
                hash_value(consensus["raw_sha256"]) and
                utc(consensus["pre_event_capture_utc"]) < deadline,
                "INVALID_PRE_RELEASE_CONSENSUS")
        require(isinstance(consensus.get("source_url"), str) and
                consensus["source_url"].startswith("https://") and
                isinstance(consensus.get("methodology"), str) and
                bool(consensus["methodology"].strip()), "UNSOURCED_CONSENSUS")
    for indicator in c["indicative_external_forecasts"]:
        require(indicator["kind"] == "INDICATIVE_ONLY" and
                indicator["captured_before_release"] is True and
                number(indicator["value"]) >= 0, "INDICATIVE_MISCLASSIFIED")
        require(github_path(indicator["source"]), "INDICATIVE_SOURCE_MISSING")
    outcome = c["official_outcome"]
    require(outcome["status"] in {"NOT_RELEASED", "RESEARCH_BRANCH_RAW_CAPTURED"},
            "OUTCOME_STATUS_UNKNOWN")
    score = c["score"]
    require(score["rule"] == "ABSOLUTE_ERROR_LOWER_BETTER" and
            score["out_of_sample_edge_verified"] is False, "SCORING_RULE_CHANGED")
    if outcome["status"] == "NOT_RELEASED":
        require(all(outcome[k] is None for k in ("value", "raw_sha256", "capture_utc", "evidence_link")),
                "FUTURE_OUTCOME_INVENTED")
        require(all(score[k] is None for k in ("v0_absolute_error", "consensus_absolute_error",
                                               "v1_absolute_error")), "FUTURE_SCORE_INVENTED")
    else:
        require(outcome["value"] is not None and
                hash_value(outcome["raw_sha256"]) and
                utc(outcome["capture_utc"]) >= deadline and
                isinstance(outcome["evidence_link"], str) and
                outcome["evidence_link"].startswith("https://github.com/"),
                "OUTCOME_NEEDS_ORIGINAL_AND_CAPTURE")
        require(score["v0_absolute_error"] is not None and
                number(score["v0_absolute_error"]) ==
                abs(number(outcome["value"]) - number(f["value"])), "OUTCOME_SCORE_WRONG")
        if consensus["status"] == "NOT_VERIFIED":
            require(score["consensus_absolute_error"] is None, "CONSENSUS_SCORE_WITHOUT_CONSENSUS")
        else:
            require(number(score["consensus_absolute_error"]) ==
                    abs(number(outcome["value"]) - number(consensus["value"])),
                    "CONSENSUS_SCORE_WRONG")
        require(score["v1_absolute_error"] is None, "V1_SCORE_NOT_REGISTERED")
    d = c["decision"]
    require(d["engineering"] == "PASS_RESEARCH_GATE" and
            d["investment"] == "NO_GO" and d["trade_eligible"] is False,
            "UNAUTHORIZED_INVESTMENT_PROMOTION")
    return c


def load_portfolio(root: Path = HERE):
    m = validate_manifest(read_json(root / "status_manifest.json"))
    cards = []
    prs = {p["number"]: p for p in m["prs"]}
    for path in m["research_cards"]:
        # Restrict paths to this root; do not open arbitrary files in repo.
        require(path.startswith("research_overview/cards/"), "UNSAFE_CARD_DIRECTORY")
        card = validate_card(read_json(root / "cards" / Path(path).name), prs)
        cards.append(card)
    require({c["hypothesis_id"] for c in cards} == {"H-CORN-001", "H-NG-001"},
            "PORTFOLIO_HYPOTHESES_MISSING")
    require({c["research_pr"] for c in cards} == {22, 23}, "HYPOTHESIS_PR_MISMATCH")
    by_id = {c["hypothesis_id"]: c for c in cards}
    require(by_id["H-CORN-001"]["unit"] == "million_bushels" and
            by_id["H-CORN-001"]["forecast"]["value"] == 1758 and
            by_id["H-CORN-001"]["event_id"] == "USDA-WASDE-2026-12-10",
            "CORN_FROZEN_BASELINE_CHANGED")
    require(by_id["H-NG-001"]["unit"] == "Bcf" and
            by_id["H-NG-001"]["forecast"]["value"] == 61 and
            by_id["H-NG-001"]["event_id"] == "EIA-WNGSR-2026-11-19",
            "NATGAS_FROZEN_BASELINE_CHANGED")
    require(by_id["H-CORN-001"]["forecast"]["source_path"] ==
            "research_core/k4/cases/2026-12-10-forward-baseline-forecast.json" and
            by_id["H-CORN-001"]["forecast"]["source_git_blob_sha1"] ==
            "ad00e4c0989d98eae56b31960fc9c24cd76da120" and
            by_id["H-CORN-001"]["evidence"]["source_git_blob_sha1"] ==
            "9102c9c4e66dd0239d043a5c2c756ecb678bfffe",
            "CORN_ORIGINAL_LINK_IDENTITY_CHANGED")
    require(by_id["H-NG-001"]["forecast"]["source_git_blob_sha1"] ==
            "bacc82f549fb3bba74142139d89bec94e386d88e" and
            by_id["H-NG-001"]["evidence"]["source_git_blob_sha1"] ==
            "8fb2ef46421b9a4af513f54e298aef45943a79b5",
            "NATGAS_ORIGINAL_LINK_IDENTITY_CHANGED")
    return m, cards
