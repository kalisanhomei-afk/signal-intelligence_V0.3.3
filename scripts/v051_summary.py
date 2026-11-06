#!/usr/bin/env python3
"""GitHub Actions audit summary; never claim publication-level headline matching is fact verification."""
import json,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    x=json.loads((ROOT/'data/benchmark_audit_v051.json').read_text(encoding='utf-8'))['meta']
    lines=['\n## SIGNAL V0.5.1｜重要事件參考庫與漏報驗收門檻\n',
           '> 官方發布網址已整理為「參考候選」；**重要性與事件對應尚待人工審核**。來源頁面存在不代表全球重要、事件已獨立證實。\n',
           f'參考候選：{x["gold_candidate_total"]}；人工批准：{x["approved_benchmark_events"]}；人工完成資料匹配：{x["match_adjudications_within_retention"]}。\n',
           f'已確認收錄：{x["reviewed_present"]}；已確認缺漏：{x["reviewed_absent"]}；需至少 {x["minimum_approved_events"]} 起獨立事件、{x["minimum_domains"]} 領域與 {x["minimum_regions"]} 地區才可展示「人工樣本命中率」。\n',
           '跨來源證據驗證：尚未實施；AI 重要性評分：尚未實施；**全球重大事件遺漏率：不可量測**。\n',
           f'人工樣本是否達展示條件：{"是" if x["benchmark_ready"] else "否"}；最大領域占比 {x["largest_domain_share"] if x["largest_domain_share"] is not None else "尚無"}（上限 35%）。\n',
           '提醒：如果所有參考事件都來自宏觀經濟，即使批准 20 件也可能無法通過領域分散門檻；不可為了達標直接批量核准。\n']
    t='\n'.join(lines)
    print(t)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'],'a',encoding='utf-8') as f:f.write(t)
if __name__=='__main__':main()
