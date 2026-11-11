"""SIGNAL K1: deterministic, offline, synthetic-only data-contract demonstration.

Run from repository root: python -m research_core.demo
"""
from __future__ import annotations
import json
import html
from dataclasses import asdict, replace
from pathlib import Path
from datetime import datetime, timezone
from .contracts import ContractError, SourceSnapshot, Observation, EventSignal
from .store import ImmutableStore
from .asof_guard import check_asof, select_asof
from .stockflow import check_balance

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
FIXTURE_FILE = ROOT / "fixtures" / "synthetic_corn_vintages.json"


def jwrite(name: str, data: object):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_fixture():
    dataset = json.loads(FIXTURE_FILE.read_text(encoding="utf-8"))
    if dataset.get("fixture_type") != "SYNTHETIC_ONLY_NOT_USDA":
        raise ContractError("FIXTURE_UNVERIFIED", "K1 requires expressly synthetic fixture data")
    return dataset


def populate_store(store: ImmutableStore, data: dict):
    for source in data["snapshots"]:
        payload = source["raw_payload_utf8"].encode("utf-8")
        snap = SourceSnapshot(**{k: v for k, v in source.items() if k != "raw_payload_utf8"})
        store.add_snapshot(snap, payload)
    for observation in data["observations"]:
        store.add_observation(Observation(**observation))


def replay_view(selected: dict[str, Observation], snapshots: dict[str, SourceSnapshot]):
    return [
        {
            **asdict(obs),
            "source_uri": snapshots[obs.snapshot_id].source_uri,
            "published_at": snapshots[obs.snapshot_id].published_at,
            "retrieved_at": snapshots[obs.snapshot_id].retrieved_at,
            "payload_sha256": snapshots[obs.snapshot_id].payload_sha256,
        }
        for _series_id, obs in sorted(selected.items())
    ]


def expect_rejection(name: str, expected_code: str, action):
    try:
        action()
    except ContractError as exc:
        return {
            "case": name, "expectation": "REJECT", "observed": "REJECT",
            "code": exc.code, "detail": exc.detail, "passed": exc.code == expected_code,
        }
    except Exception as exc:
        return {
            "case": name, "expectation": "REJECT", "observed": "UNEXPECTED_ERROR",
            "code": type(exc).__name__, "detail": str(exc), "passed": False,
        }
    return {
        "case": name, "expectation": "REJECT", "observed": "ACCEPTED_UNEXPECTEDLY",
        "code": None, "detail": "negative test unexpectedly accepted", "passed": False,
    }


def run_qa(store: ImmutableStore, observations: list[Observation], snapshots: dict[str, SourceSnapshot], asof: str) -> list[dict]:
    obs_v1 = [o for o in observations if o.vintage_id == "v1"]
    obs_v2 = [o for o in observations if o.vintage_id == "v2"]
    source1 = snapshots[obs_v1[0].snapshot_id]
    cases = [
        expect_rejection("future_data_leakage", "FUTURE_DATA", lambda: check_asof(obs_v2[0], snapshots[obs_v2[0].snapshot_id], asof)),
        expect_rejection("revision_cannot_overwrite", "IMMUTABLE_VINTAGE", lambda: store.add_observation(obs_v1[0])),
        expect_rejection("monthly_data_cannot_replace_marketing_year", "PERIOD_MISMATCH", lambda: check_balance([
            replace(o, frequency="month", period="2026-01") if o.series_id == "imports" else o for o in obs_v1
        ])),
        expect_rejection("bushels_cannot_become_tonnes", "UNIT_MISMATCH", lambda: check_balance([
            replace(o, unit="metric_tons") if o.series_id == "imports" else o for o in obs_v1
        ])),
        expect_rejection("price_change_does_not_prove_production_cause", "CAUSAL_OVERCLAIM", lambda: EventSignal(
            "EV-SYN-01", asof, "corn_price_jump", [obs_v1[0].observation_id], ["yield_drop"], causal_status="causally_proven"
        )),
        expect_rejection("source_vintage_mismatch", "VINTAGE_MISMATCH", lambda: check_asof(
            replace(obs_v1[0], vintage_id="v2"), source1, asof
        )),
    ]
    bad_balance = [replace(o, value="1700") if o.series_id == "ending_stocks" else o for o in obs_v1]
    balance_result = check_balance(bad_balance)
    cases.append({
        "case": "unbalanced_inventory_flagged_not_corrected", "expectation": "FLAG",
        "observed": "FLAG" if not balance_result.balanced and balance_result.reported_ending == "1700" else "INCORRECT",
        "code": "BALANCE_DISCREPANCY", "detail": f"reported={balance_result.reported_ending}; calculated={balance_result.calculated_ending}",
        "passed": not balance_result.balanced and balance_result.reported_ending == "1700",
    })
    return cases


def review_html(pre: dict, post: dict, model_inputs: dict, qa: dict) -> str:
    esc = html.escape
    input_rows = "\n".join(
        f"<tr><td><code>{esc(item['series_id'])}</code></td><td class='val'>{esc(item['value'])}</td><td>{esc(item['unit'])}</td><td><code>{esc(item['vintage_id'])}</code></td><td>{esc(item['available_at'])}</td></tr>"
        for item in model_inputs["inputs"]
    )
    qa_rows = "\n".join(
        f"<tr><td>{esc(case['case'])}</td><td>{esc(case['expectation'])}</td><td><span class='tag'>{esc(case['observed'])}</span></td><td><code>{esc(str(case['code']))}</code></td><td>{'通過' if case['passed'] else '失敗'}</td></tr>"
        for case in qa["cases"]
    )
    sections = f"""
    <div class="note"><strong>完全合成的工程測試資料</strong>　不是 USDA 官方觀測值、不是市場報價、不是投資預測或建議。</div>
    <div class="grid">
        <div class="card"><div class="label">K1 驗收狀態</div><div class="big">{'PASS' if qa['all_passed'] else 'FAIL'}</div><p>{qa['passed_cases']} / {qa['case_count']} 項合成反例／會計檢查</p></div>
        <div class="card"><div class="label">資料版本</div><div class="big">2</div><p>原始版本與後續修訂均保留</p></div>
        <div class="card"><div class="label">預測前可用資料</div><div class="big">{len(pre['selected'])}</div><p>v1；沒有使用 v2 未來修訂值</p></div>
        <div class="card"><div class="label">期末庫存一致性</div><div class="big">{'PASS' if model_inputs['balance']['balanced'] else 'FLAG'}</div><p>輸入期末值 {esc(model_inputs['balance']['reported_ending'])} 百萬蒲式耳</p></div>
    </div>
    <section><h2>01｜時點重播：資料不是永遠只有最新版</h2>
      <p>模擬研究截止時間：<code>{esc(pre['as_of'])}</code>。截至該時點，僅 v1 可用。後續的 <code>v2</code> 必須留在資料庫，但不能回寫到當時的研究結果。</p>
      <div class="timeline"><div><b>v1｜首次模擬公開</b><span>2026-01-10</span><p>產量 <strong>15,000</strong>、期末庫存 <strong>1,625</strong>（百萬蒲式耳）</p></div>
      <div><b>v2｜後續合成修訂</b><span>2026-01-15</span><p>產量 <strong>14,900</strong>、期末庫存 <strong>1,525</strong>（百萬蒲式耳）</p></div></div>
      <p class="subtle">此為完全虛構示例；用來證明後續修訂不會污染較早日期的模型輸入。</p>
    </section>
    <section><h2>02｜研究時點的乾淨輸入</h2>
      <div class="scroll"><table><thead><tr><th>變數</th><th>值</th><th>單位</th><th>版本</th><th>公開時間</th></tr></thead><tbody>{input_rows}</tbody></table></div>
      <p>會計檢查：期初庫存 + 產量 + 進口 − 國內使用 − 出口 = <strong>{esc(model_inputs['balance']['calculated_ending'])}</strong>（百萬蒲式耳）。資料表示期末庫存為 <strong>{esc(model_inputs['balance']['reported_ending'])}</strong>。差額 <strong>{esc(model_inputs['balance']['discrepancy'])}</strong>。</p>
      <p class="subtle">同一版本、同一期間、同一國家與商品、同一統計口徑，才可放進這張表。K1 沒有預測未來價格。</p>
    </section>
    <section><h2>03｜故意錯誤案例與攔截結果</h2>
      <div class="scroll"><table><thead><tr><th>案例</th><th>預期</th><th>實際</th><th>程式代碼</th><th>檢驗</th></tr></thead><tbody>{qa_rows}</tbody></table></div>
    </section>
    <section><h2>04｜已完成／尚未完成</h2>
      <div class="split"><div><h3>已完成 K1</h3><p>來源快照雜湊、不可覆寫版本、時點限制、單位規範、供需平衡、因果推論狀態約束、可重播的離線測試。</p></div>
      <div><h3>尚未完成 K2/K3</h3><p>事件引擎、主動推演預測、真實 USDA 資料接入、與市場預期比較、期貨報價、資產配置／投資績效。</p></div></div>
    </section>"""
    return f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SIGNAL K1｜共同研究核心離線驗收</title>
    <style>
    :root{{--bg:#0d1118;--panel:#151b23;--line:#3b3a2d;--gold:#dcc180;--text:#f1eee5;--muted:#b3bdc7;--success:#8bd3b1}}
    *{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font-family:'Microsoft JhengHei',system-ui,sans-serif;line-height:1.7}}
    .wrap{{max-width:1120px;margin:auto;padding:36px 22px 70px}}.kicker{{color:var(--gold);font-weight:700;letter-spacing:3px;font-size:12px}}h1{{margin:8px 0 10px;font-size:clamp(30px,4vw,48px);line-height:1.2}}h2{{font-size:21px;color:var(--gold);margin:0 0 16px}}h3{{margin:0 0 10px;color:var(--gold)}}p{{margin:10px 0}}.muted,.subtle{{color:var(--muted)}}.lede{{max-width:810px;color:#d7dee6;font-size:16px}}.note{{margin:26px 0;padding:15px 20px;background:#33291a;border:1px solid #9d824c;border-radius:10px;color:#ffe5ac}}.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:20px 0 24px}}.card,section{{background:var(--panel);border:1px solid var(--line);border-radius:14px}}.card{{padding:18px}}.label{{font-size:13px;color:var(--muted)}}.big{{font-size:29px;font-weight:800;color:var(--success);margin:5px 0}}.card p{{font-size:12px;color:var(--muted)}}section{{padding:25px;margin:19px 0}}code{{font-family:ui-monospace,Consolas,monospace;font-size:12px;color:#e9cd8a;overflow-wrap:anywhere}}table{{width:100%;border-collapse:collapse;min-width:610px;font-size:13px}}th{{color:var(--gold);text-align:left;border-bottom:1px solid #6b5a39;padding:10px 8px}}td{{padding:11px 8px;border-bottom:1px solid #303741}}.val{{font-weight:800;color:#fff;text-align:right}}.scroll{{overflow-x:auto}}.tag{{padding:2px 8px;background:#203b31;color:#a1dec3;border-radius:4px}}.timeline{{display:flex;gap:16px}}.timeline>div{{flex:1;padding:15px;border-left:3px solid var(--gold);background:#1b232d;border-radius:4px}}.timeline span{{display:block;color:var(--muted);font-size:12px}}.split{{display:grid;grid-template-columns:1fr 1fr;gap:23px}}footer{{color:var(--muted);font-size:12px;margin-top:27px}}@media(max-width:780px){{.grid{{grid-template-columns:1fr 1fr}}.timeline,.split{{display:block}}.timeline>div{{margin-bottom:12px}}section{{padding:18px}}}}@media(max-width:450px){{.grid{{grid-template-columns:1fr 1fr;gap:8px}}.card{{padding:12px}}.big{{font-size:23px}}}}
    </style></head><body><main class="wrap"><div class="kicker">視界 SIGNAL / RESEARCH CORE / K1</div><h1>先讓資料能夠<br>被正確地用於預測</h1><p class="lede">雙引擎共同研究核心第一道驗收：來源、版本、時點、單位與存量流量一致性。所有數值均為合成示例。</p>{sections}<footer>SIGNAL K1 offline / Synthetic fixture only / No AI API / No market price / No live trading / No main deployment</footer></main></body></html>"""


def build_demo():
    fixture = load_fixture()
    with ImmutableStore(":memory:") as store:
        populate_store(store, fixture)
        observations = store.all_observations()
        snapshots = store.all_snapshots()
        early_time = fixture["as_of_before_revision"]
        later_time = fixture["as_of_after_revision"]
        early = select_asof(observations, snapshots, early_time)
        later = select_asof(observations, snapshots, later_time)
        if len(early) != 6 or len(later) != 6:
            raise RuntimeError("K1 demo failed: expected six as-of observations each")
        catalog = {
            "data_type": "SYNTHETIC_ONLY_NOT_USDA", "snapshots": [asdict(s) for s in snapshots.values()],
            "observations": [
                {
                    **asdict(o),
                    "source_uri": snapshots[o.snapshot_id].source_uri,
                    "published_at": snapshots[o.snapshot_id].published_at,
                    "retrieved_at": snapshots[o.snapshot_id].retrieved_at,
                } for o in observations
            ],
        }
        early_view = {"as_of": early_time, "knowledge_policy": "system_retrieval_required", "selected": replay_view(early, snapshots)}
        later_view = {"as_of": later_time, "knowledge_policy": "system_retrieval_required", "selected": replay_view(later, snapshots)}
        replay = {"data_type": "SYNTHETIC_ONLY_NOT_USDA", "early": early_view, "after_revision": later_view,
                  "vintage_policy": "latest eligible, do not mutate original vintage"}
        balance = check_balance(list(early.values()))
        model_inputs = {"data_type": "SYNTHETIC_ONLY_NOT_USDA", "as_of": early_time,
            "model_ready_for_contract_testing": balance.balanced,
            "not_a_forecast": True, "inputs": early_view["selected"], "balance": balance.as_dict()}
        cases = run_qa(store, observations, snapshots, early_time)
        qa = {"test_mode": "synthetic_contract_negative_cases", "case_count": len(cases),
              "passed_cases": sum(x["passed"] for x in cases), "all_passed": all(x["passed"] for x in cases),
              "cases": cases, "no_api_calls": True, "data_type": "SYNTHETIC_ONLY_NOT_USDA"}
        jwrite("observation_catalog.json", catalog)
        jwrite("asof_replay.json", replay)
        jwrite("model_inputs.json", model_inputs)
        jwrite("qa_report.json", qa)
        (OUT / "review.html").write_text(review_html(early_view, later_view, model_inputs, qa), encoding="utf-8")
        if not qa["all_passed"] or not balance.balanced:
            raise RuntimeError("K1 contract QA did not pass; see research_core/out/qa_report.json")
        return qa


if __name__ == "__main__":
    report = build_demo()
    print(f"K1 synthetic offline QA: {report['passed_cases']}/{report['case_count']} negative/consistency cases PASS")
    print(f"Report: {OUT / 'review.html'}")
