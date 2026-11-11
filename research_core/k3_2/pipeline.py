#!/usr/bin/env python3
"""SIGNAL K3.2: provenance-preserving corn balance audit, not a forecast/trade model."""
from __future__ import annotations
import argparse
import csv
import hashlib
import html
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
COLS = ["planted_million_acres", "harvested_million_acres", "yield_bushels_per_acre",
        "beginning_stocks_million_bushels", "production_million_bushels", "imports_million_bushels",
        "feed_residual_million_bushels", "food_seed_industrial_million_bushels",
        "domestic_total_million_bushels", "exports_million_bushels",
        "total_use_million_bushels", "ending_stocks_million_bushels"]
STOCK_TERMS = ("beginning_stocks_million_bushels", "production_million_bushels",
               "imports_million_bushels", "domestic_total_million_bushels", "exports_million_bushels")
EPS = 0.00001


def parse_datetime(s: str) -> datetime:
    d = datetime.fromisoformat(s)
    if d.utcoffset() is None:
        raise ValueError("release_at must include explicit timezone offset")
    return d.astimezone(timezone.utc)


def load_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_balances(rows: list[dict]) -> list[dict]:
    if not rows:
        raise ValueError("At least one official balance row is required")
    checked, seen = [], set()
    for r in rows:
        for k in ["release_at", "marketing_year", "commodity", "country", "source_url", "verification", *COLS]:
            if not r.get(k):
                raise ValueError(f"Missing required field: {k}")
        when = parse_datetime(r["release_at"])
        key = (when.isoformat(), r["marketing_year"], r["commodity"], r["country"])
        if key in seen:
            raise ValueError(f"Duplicate release+year+product+country: {key}")
        seen.add(key)
        if (r["commodity"], r["country"]) != ("CORN", "US"):
            raise ValueError("Only U.S. corn is supported in K3.2")
        if not r["source_url"].startswith("https://www.usda.gov/oce/commodity/wasde/"):
            raise ValueError("Official balance rows must cite their original USDA WASDE document")
        if r["verification"] != "official_release_text_checked":
            raise ValueError("Only checked primary release text may be used in official balance audits")
        f = {k: float(r[k]) for k in COLS}
        if not all(v >= 0 for v in f.values()):
            raise ValueError("Negative balance component")
        if f["planted_million_acres"] < f["harvested_million_acres"]:
            raise ValueError("Harvested area exceeds planted area")
        if abs(f["harvested_million_acres"] * f["yield_bushels_per_acre"] - f["production_million_bushels"]) > 12.0:
            raise ValueError("Yield × harvested acres inconsistent with production beyond rounding tolerance")
        if abs(f["feed_residual_million_bushels"] + f["food_seed_industrial_million_bushels"] - f["domestic_total_million_bushels"]) > EPS:
            raise ValueError("Domestic components do not equal domestic total")
        if abs(f["domestic_total_million_bushels"] + f["exports_million_bushels"] - f["total_use_million_bushels"]) > EPS:
            raise ValueError("Exports plus domestic use do not equal total use")
        computed = (f["beginning_stocks_million_bushels"] + f["production_million_bushels"]
                    + f["imports_million_bushels"] - f["domestic_total_million_bushels"]
                    - f["exports_million_bushels"])
        if abs(computed - f["ending_stocks_million_bushels"]) > EPS:
            raise ValueError(f"Balance-sheet identity failed: calculated={computed}, actual={f['ending_stocks_million_bushels']}")
        checked.append({"release_at": r["release_at"], "marketing_year": r["marketing_year"],
                        "commodity": "CORN", "country": "US", **f,
                        "source_url": r["source_url"], "verification": r["verification"],
                        "computed_ending_stocks": computed, "residual": round(computed-f["ending_stocks_million_bushels"], 6),
                        "release_utc": when.isoformat()})
    return sorted(checked, key=lambda r: r["release_utc"])


def bridge(prev: dict, cur: dict) -> dict:
    if prev["marketing_year"] != cur["marketing_year"]:
        raise ValueError("Do not bridge across distinct marketing years")
    c = {name: round(cur[name]-prev[name], 6) for name in STOCK_TERMS}
    result = round(c["beginning_stocks_million_bushels"] + c["production_million_bushels"]
                   + c["imports_million_bushels"] - c["domestic_total_million_bushels"]
                   - c["exports_million_bushels"], 6)
    observed = round(cur["ending_stocks_million_bushels"]-prev["ending_stocks_million_bushels"], 6)
    if abs(result-observed) > EPS:
        raise ValueError("Change attribution failed")
    return {"prior_release": prev["release_at"], "current_release": cur["release_at"],
            "marketing_year": cur["marketing_year"], "raw_deltas": c,
            "ending_stocks_delta": observed, "accounting_bridge_delta": result,
            "contributions_to_stock_delta": {
                "beginning_stocks": c["beginning_stocks_million_bushels"],
                "production": c["production_million_bushels"],
                "imports": c["imports_million_bushels"],
                "domestic_use": -c["domestic_total_million_bushels"],
                "exports": -c["exports_million_bushels"]},
            "classification": "accounting_attribution_not_causal_identification"}


def k31_summary(path: Path | None, official: list[dict]) -> dict:
    if not path or not path.is_file():
        return {"status": "MISSING_K31_INPUT", "message": "No K3.1 dataset supplied; cannot cross-check chronology"}
    vintages = load_csv(path)
    known = {(r["release_utc"], r["marketing_year"]):r for r in official}
    matches, mismatches = [], []
    by_year = defaultdict(list)
    for v in vintages:
        if v.get("metric") != "ending_stocks" or v.get("commodity") != "CORN" or v.get("country") != "US" or v.get("unit") != "million_bushels":
            raise ValueError("Unexpected K3.1 vintage metric/unit")
        t = parse_datetime(v["release_at"])
        obj = {"release_at": v["release_at"], "marketing_year": v["marketing_year"], "value":float(v["value"]), "t":t}
        by_year[v["marketing_year"]].append(obj)
        org = known.get((t.isoformat(),v["marketing_year"]))
        if org:
            (matches if abs(float(v["value"])-org["ending_stocks_million_bushels"])<EPS else mismatches).append(
                {"release_at":v["release_at"], "k31": float(v["value"]), "official":org["ending_stocks_million_bushels"]})
    changes = []
    for year, vals in by_year.items():
        vals.sort(key=lambda x:x["t"])
        for p, c in zip(vals, vals[1:]):
            changes.append({"marketing_year":year, "release_at":c["release_at"],
                            "absolute_change_million_bushels":abs(c["value"]-p["value"])})
    mae = round(sum(x["absolute_change_million_bushels"] for x in changes)/len(changes), 4) if changes else None
    return {"status":"CROSSCHECKED" if not mismatches else "OFFICIAL_CONFLICT_STOP",
            "rows":len(vintages), "monthly_transitions":len(changes),
            "previous_vintage_naive_mae_million_bushels":mae,
            "matched_official_rows":matches, "conflicts":mismatches, "sha256":digest(path)}


def load_historical(path: Path | None) -> dict:
    if not path or not path.is_file():
        return {"status":"NOT_IMPORTED", "records":0, "transitions":0, "marketing_years":[],
                "backtest_ready":False, "message":"Download/import the official historical consolidated WASDE CSV after validation."}
    records = load_csv(path)
    if not records:
        raise ValueError("Historical CSV is empty")
    by_year, keys = defaultdict(list), set()
    for r in records:
        for key in ("release_at","marketing_year","metric","value","unit","source_url","verification"):
            if not r.get(key):
                raise ValueError(f"History missing {key}")
        t=parse_datetime(r["release_at"])
        if r["metric"] != "ending_stocks" or r["unit"]!="million_bushels" or r["verification"]!="official_consolidated_vintage":
            raise ValueError("Unexpected historical metric/unit/provenance")
        if not r["source_url"].startswith("https://www.usda.gov/sites/default/files/documents/"):
            raise ValueError("Historical source must be published official USDA CSV")
        signature=(r["marketing_year"],t.isoformat())
        if signature in keys: raise ValueError("Historical duplicate vintage")
        keys.add(signature)
        by_year[r["marketing_year"]].append((t,float(r["value"])))
    transitions=[]
    for y, observations in by_year.items():
        for p,c in zip(sorted(observations),sorted(observations)[1:]):
            transitions.append(abs(c[1]-p[1]))
    # A minimum count is a *collection readiness* gate, not evidence of model quality.
    ready=len(transitions)>=24 and len(by_year)>=3
    return {"status":"HISTORY_READY_FOR_EXPERIMENT_DESIGN" if ready else "INSUFFICIENT_HISTORY",
            "records":len(records),"transitions":len(transitions),"marketing_years":sorted(by_year),
            "previous_vintage_naive_mae_million_bushels":round(sum(transitions)/len(transitions),4) if transitions else None,
            "backtest_ready":ready, "sha256":digest(path),
            "note":"Even READY means data volume only; covariates, pre-publication timestamps and holdout tests remain mandatory."}


def render_html(report: dict) -> str:
    H=html.escape
    bal=report["official_balances"]
    rows=''.join('<tr>'+''.join(f'<td>{H(str(row[x]))}</td>' for x in ("release_at","yield_bushels_per_acre", "production_million_bushels", "domestic_total_million_bushels","exports_million_bushels","ending_stocks_million_bushels", "residual"))+'</tr>' for row in bal)
    b=report["month_to_month_bridges"]
    bridges=''.join('<tr>'+''.join(f'<td>{H(str(x))}</td>' for x in (x["prior_release"][:10]+" → "+x["current_release"][:10],x["ending_stocks_delta"],x["contributions_to_stock_delta"]["production"],x["contributions_to_stock_delta"]["domestic_use"],x["contributions_to_stock_delta"]["exports"]))+'</tr>' for x in b)
    historical=report["historical_intake"]
    k31=report["k31_comparison"]
    return f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>SIGNAL K3.2 | 玉米供需平衡稽核</title><style>body{{background:#0a1323;color:#eaf1ff;font-family:system-ui,'Noto Sans TC',sans-serif;max-width:1020px;margin:40px auto;padding:0 20px;line-height:1.7}}h1{{font-size:32px}}.brand{{letter-spacing:.25em;color:#91b6f2}}.callout{{border:1px solid #3c6087;background:#15263c;padding:20px;margin:18px 0}}table{{width:100%;border-collapse:collapse;font-size:14px}}th,td{{border-bottom:1px solid #35485d;text-align:right;padding:11px}}th:first-child,td:first-child{{text-align:left}}.wrap{{overflow-x:auto}}.muted{{color:#a5bfd6}}.tag{{color:#9fe6be}}a{{color:#9ccaf4}}</style></head><body><div class="brand">視界 SIGNAL · RESEARCH EVIDENCE</div><h1>K3.2｜USDA 玉米供需存量流量稽核</h1><div class="callout"><strong>狀態：{H(report['status'])}</strong><p>官方原始報告：{len(bal)} 期；供需平衡通過：{len(bal)} 期。<br>新增模型：0；可交易訊號：否；自動發布：否。</p></div><h2>官方報告資料（美國 2026/27 玉米）</h2><p class="muted">產量、需求與庫存單位均為百萬蒲式耳；單產為蒲式耳／英畝。</p><div class="wrap"><table><thead><tr><th>公布時間（含時區）</th><th>單產</th><th>產量</th><th>國內使用</th><th>出口</th><th>期末庫存</th><th>平衡殘差</th></tr></thead><tbody>{rows}</tbody></table></div><h2>期末庫存修正歸因</h2><div class="wrap"><table><thead><tr><th>報告</th><th>庫存變動</th><th>產量貢獻</th><th>國內使用貢獻</th><th>出口貢獻</th></tr></thead><tbody>{bridges or '<tr><td>尚無同年度連續期數</td></tr>'}</tbody></table></div><p class="muted">橋接歸因是會計恆等式，不能證明天氣直接造成價格變動或 USDA 修正。</p><h2>歷史樣本與預測門檻</h2><div class="callout">官方歷史匯入狀態：<span class="tag">{H(historical['status'])}</span>　｜　歷史修正：{historical['transitions']}　｜　收成年度：{len(historical['marketing_years'])}<br>K3.1 對照：{H(k31['status'])}　｜　基準 MAE：{H(str(k31.get('previous_vintage_naive_mae_million_bushels')))} 百萬蒲式耳<br>後續要求：≥24 次修正、≥3 個收成年度、發布時點驗證、真正的 walk-forward out-of-sample 評分。</div><h2>研究紀律</h2><p>本頁只代表已核對報告的存量流量運算，不代表前瞻預測已成立。完整記錄與每個輸入的 SHA-256 請查閱 <code>review.json</code>。</p><p class="muted">資料：USDA WASDE October 2026 / November 2026，詳見來源連結。</p></body></html>'''


def generate(official_path: Path, k31_path: Path | None, history_path: Path | None, output: Path) -> dict:
    bal=validate_balances(load_csv(official_path))
    by_year=defaultdict(list)
    for r in bal:by_year[r["marketing_year"]].append(r)
    bridges=[]
    for v in by_year.values():
        for p,c in zip(v,v[1:]): bridges.append(bridge(p,c))
    k31=k31_summary(k31_path,bal)
    hist=load_historical(history_path)
    state="DATA_CONFLICT_REQUIRES_REVIEW" if k31["status"] == "OFFICIAL_CONFLICT_STOP" else "RESEARCH_ONLY_NO_TRAINED_MODEL"
    result={"version":"K3.2", "status":state,"scope":"US CORN balance sheets / 2026-27",
            "forecast_model_trained":False,"trading_signal":False,"pages_published":False,
            "source_sha256":{"official_corn_balances":digest(official_path)},
            "official_balances":bal,"month_to_month_bridges":bridges,"historical_intake":hist,
            "k31_comparison":k31,"warning":"Quantities identify revisions, not their causal sources. Do not use a next-month USDA forecast as a pre-report input."}
    output.mkdir(parents=True,exist_ok=True)
    (output/'review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    (output/'review.html').write_text(render_html(result),encoding='utf-8')
    return result


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--official',type=Path,default=HERE/'inputs'/'official_corn_balances.csv')
    p.add_argument('--k31',type=Path,default=HERE.parent/'k3_1'/'inputs'/'wasde_vintages.csv')
    p.add_argument('--historical',type=Path,default=HERE/'inputs'/'historical_vintages.csv')
    p.add_argument('--output',type=Path,default=HERE/'out')
    args=p.parse_args()
    x=generate(args.official,args.k31,args.historical,args.output)
    print(json.dumps({k:v for k,v in x.items() if k in ('status','source_sha256','historical_intake','k31_comparison')},ensure_ascii=False,indent=2))
    if x['status']=='DATA_CONFLICT_REQUIRES_REVIEW':raise SystemExit(2)

if __name__=='__main__':main()
