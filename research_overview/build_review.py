"""Build a standalone, safe, read-only SIGNAL research review from validated JSON.

Local preview only; output is not a production deployment or live data feed.
"""
from __future__ import annotations
import argparse
from html import escape
import json
from pathlib import Path
from urllib.parse import quote

from research_overview.validate import HERE, load_portfolio

STATUS_ZH = {
    "PARTIAL_PROTOTYPE": "原型／部分驗證",
    "RESEARCH_VERIFIED": "研究工程已驗收",
    "NOT_VALIDATED": "尚無有效性證據",
    "NOT_IMPLEMENTED": "尚未實作",
    "WAITING_OFFICIAL_OUTCOME": "等待官方公布",
    "PASS_RESEARCH_GATE": "研究工程通過",
    "NO_GO": "投資 No-Go",
}
UNIT_ZH = {"Bcf": "Bcf", "million_bushels": "百萬蒲式耳"}


def t(value) -> str:
    if value is None:
        return "待驗證"
    return escape(str(value), quote=True)


def pr_url(repo, number):
    return f"https://github.com/{quote(repo, safe='/')}/pull/{int(number)}"


def source_url(repo, branch, path):
    return f"https://github.com/{quote(repo, safe='/')}/blob/{quote(branch, safe='/')}/{quote(path, safe='/')}"


def render_card(c, repo):
    forecast = c["forecast"]
    outcome = c["official_outcome"]
    consensus = c["market_consensus"]
    score = c["score"]
    value = f'{t(forecast["value"])} {t(UNIT_ZH[c["unit"]])}'
    if outcome["status"] == "NOT_RELEASED":
        actual = "尚未取得正式結果"
        error = "—"
    else:
        actual = f'{t(outcome["value"])} {t(UNIT_ZH[c["unit"]])}'
        error = f'{t(score["v0_absolute_error"])} {t(UNIT_ZH[c["unit"]])}'
    consensus_text = "尚無合格的公告前共識" if consensus["status"] == "NOT_VERIFIED" else (
        f'{t(consensus["value"])} {t(UNIT_ZH[c["unit"]])}'
    )
    reference = "".join(
        f'<li>{t(x["name"])}：{t(x["value"])} {t(UNIT_ZH[c["unit"]])}'
        '（僅日曆／參考預測，不屬於已核實共識）</li>'
        for x in c["indicative_external_forecasts"]
    )
    if not reference:
        reference = "<li>無已封存的獨立參考預測</li>"
    return f"""
    <article class="hypothesis">
      <div class="split"><div>
        <div class="eyebrow">{t(c["hypothesis_id"])} · 研究分支</div>
        <h3>{t(c["title"])}</h3>
      </div><span class="status">{t(STATUS_ZH[c["decision"]["research"]])}</span></div>
      <p class="muted">標的：{t(c["scope"])}｜公告 UTC：{t(c["release_scheduled_utc"])}</p>
      <div class="metrics">
        <div class="metric"><small>已事前凍結 V0</small><strong>{value}</strong></div>
        <div class="metric"><small>官方實際結果</small><strong>{actual}</strong></div>
        <div class="metric"><small>V0 絕對誤差</small><strong>{error}</strong></div>
        <div class="metric"><small>市場合格共識</small><strong>{consensus_text}</strong></div>
      </div>
      <div class="source">
        <strong>證據及限制</strong>
        <p>前期官方原始檔 SHA-256：<code>{t(c["evidence"]["prospective_raw_source_sha256"])}</code></p>
        <p>歷史特徵 PIT：未認證；預測增量優勢：未驗證；投資決策：<b>No-Go</b></p>
        <ul>{reference}</ul>
        <p><a href="{t(pr_url(repo, c["research_pr"]))}">研究 PR #{c["research_pr"]}</a> ·
        <a href="{t(source_url(repo, forecast["source_commit_ref"], forecast["source_path"]))}">原始凍結預測（固定提交）</a> ·
        <a href="{t(source_url(repo, c["evidence"]["source_commit_ref"], c["evidence"]["prospective_raw_source_path"]))}">已封存前期原始檔（固定提交）</a></p>
      </div>
    </article>
    """


def build_html(manifest, cards):
    layers = "\n".join(
        f"<tr><td>{t(x['name'])}</td><td>{t(STATUS_ZH[x['status']])}</td>"
        f"<td>{t(x['evidence'])}</td></tr>" for x in manifest["layers"]
    )
    prs = "\n".join(
        f"<tr><td><a href='{t(pr_url(manifest['repository'], x['number']))}'>"
        f"#{x['number']}</a></td><td>{t(x['title'])}</td>"
        f"<td>{'Draft／未合併' if x['draft'] else '僅註冊／已合併'}</td>"
        f"<td><code>{t(x['base'])}</code></td></tr>" for x in manifest["prs"]
    )
    checks = "\n".join(
        f"<tr><td>{t(x['date_time_local'].replace('T', ' '))}</td>"
        f"<td>{t(x['event'])}</td></tr>" for x in manifest["upcoming_checkpoints"]
    )
    cards_html = "\n".join(render_card(c, manifest["repository"]) for c in cards)
    datestr = t(manifest["snapshot_date"])
    version = t(manifest["publication"]["main_index_html_title"])
    return f"""<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SIGNAL｜研究系統總覽（{datestr} 快照）</title>
<style>
:root {{ color-scheme: light; font-family: system-ui,-apple-system,"Noto Sans TC","Microsoft JhengHei",sans-serif; background:#f5f6f8; color:#172337 }}
* {{ box-sizing:border-box }}
body {{ margin:0; line-height:1.55 }}
main {{ max-width:1120px; padding:34px 22px 64px; margin:auto }}
header {{ padding:30px; color:#f7f8fa; background:#152638; border-radius:15px }}
h1 {{ font-size:clamp(1.6rem,3vw,2.3rem); margin:5px 0 9px }}
h2 {{ font-size:1.4rem; margin:34px 0 15px }}
h3 {{ margin:3px 0; font-size:1.15rem }}
p {{ margin:8px 0 12px }} .muted,.eyebrow,small {{ color:#687587 }}
header .muted,header .eyebrow {{ color:#d3dce5 }}
.eyebrow {{ font-size:.78rem; letter-spacing:.05em }}
.split {{ display:flex; justify-content:space-between; align-items:flex-start; gap:12px; flex-wrap:wrap }}
.status {{ border:1px solid #ced9e4; padding:4px 10px; border-radius:20px; font-size:.78rem; color:#495c72; white-space:nowrap }}
.warning {{ border-left:4px solid #637891; background:#e9edf3; border-radius:5px; padding:14px 17px; margin-top:17px }}
.grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:16px }}
.hypothesis {{ min-width:0; padding:20px; background:white; border:1px solid #dfe4ea; border-radius:13px }}
.metrics {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px; margin:14px 0 }}
.metric {{ border:1px solid #e7ebf0; border-radius:8px; padding:12px; min-width:0 }}
.metric small {{ display:block; font-size:.77rem; margin-bottom:8px }}
.metric strong {{ font-size:1.1rem; overflow-wrap:anywhere }}
.source {{ border-top:1px solid #e2e7ee; padding-top:9px; font-size:.9rem }}
code {{ font-family:ui-monospace,Consolas,monospace; font-size:.82em; overflow-wrap:anywhere; white-space:normal }}
.tablewrap {{ overflow-x:auto; background:white; border:1px solid #e1e5eb; border-radius:12px }}
table {{ border-collapse:collapse; width:100%; min-width:630px; font-size:.88rem }}
td,th {{ text-align:left; padding:12px 14px; border-bottom:1px solid #eef0f4; vertical-align:top }}
th {{ background:#e9edf3 }}
tr:last-child td {{ border-bottom:0 }}
a {{ color:#135f91; text-decoration:underline; text-underline-offset:3px }}
ul {{ margin:9px 0; padding-left:20px }}
footer {{ margin-top:35px; color:#667384; font-size:.8rem }}
@media(max-width:760px) {{ main {{padding:18px 12px 35px}} header {{padding:21px}} .grid {{grid-template-columns:1fr}} .hypothesis {{padding:15px}} }}
</style></head><body><main>
<header><div class="eyebrow">視界 SIGNAL · RESEARCH PORTFOLIO · READ-ONLY</div>
<h1>研究進度與投資假說驗收總覽</h1>
<p>截至 {datestr} 的 GitHub 核對快照；非即時資料、正式交易系統或投資建議。</p>
<div class="eyebrow">正式主線 README：{t(manifest["publication"]["main_readme_label"])}　／　首頁程式：{version}</div>
</header>
<div class="warning"><strong>邊界說明：</strong>
main 僅註冊 K3.8 手動 Workflow，未合併 K4／K5 研究程式。
K4 與 K5 均為 Draft；原始預測及來源連結已固定到 11/17 查核的 Git commit，而不是後續會變動的分支版本。工程驗收不等於研究可獲利。所有投資權限維持 No-Go。
此報表不會自動從 GitHub 取新資料，請以快照日期核對時效。</div>
<h2>01｜投資假說驗收</h2><section class="grid">{cards_html}</section>
<h2>02｜研究系統六層架構</h2><div class="tablewrap"><table>
<thead><tr><th>架構</th><th>目前狀態</th><th>依據與限制</th></tr></thead>
<tbody>{layers}</tbody></table></div>
<h2>03｜GitHub 分支與合併範圍</h2><div class="tablewrap"><table>
<thead><tr><th>PR</th><th>工作</th><th>狀態</th><th>目標分支</th></tr></thead>
<tbody>{prs}</tbody></table></div>
<h2>04｜已安排的下一批檢查</h2><div class="tablewrap"><table>
<thead><tr><th>台灣時間 (+08:00)</th><th>交付／研究驗收</th></tr></thead>
<tbody>{checks}</tbody></table></div>
<footer>資料來源：GitHub 已核對之主線、研究 Draft PR 與既有事件封存；
本頁由 research_overview/status_manifest.json 與兩份卡片生成，並非已部署網站狀態。
官方預測誤差在原始事件未發布前均為空值。</footer>
</main></body></html>
"""


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    manifest, cards = load_portfolio()
    body = build_html(manifest, cards)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(body, encoding="utf-8")
    print(json.dumps({"status": "STATIC_RESEARCH_SNAPSHOT_GENERATED",
                      "snapshot": manifest["snapshot_date"],
                      "cards": len(cards), "output": str(args.output),
                      "auto_refreshed": False, "trade_eligible": False}))


if __name__ == "__main__":
    main()
