#!/usr/bin/env python3
"""Never imply a review queue is a checked daily news briefing."""
from pathlib import Path
import json, os
ROOT=Path(__file__).resolve().parents[1]
def main():
 doc=json.loads((ROOT/'data/daily_brief_v050.json').read_text(encoding='utf-8'))
 m=doc['meta']
 lines=['\n## SIGNAL V0.5.0｜每日情報「選讀候選」試刊\n',
       '> 只有已核准的標題、日期與原始連結。近 72 小時、來源分散的選讀候選，**不是已驗證新聞、AI 摘要、全球重大事件排行或投資建議**。\n',
       f"可選讀：{m['daily_candidate_count']} 筆；獨立發布機構：{m['daily_publishers']}；最近 7 日可用標題：{m['seven_day_source_titles']}。\n",
       f"來源最近成功更新：{m['source_last_success_at'] or '未知'}；資料過期：{'是' if m['stale_source'] else '否'}。\n",
       f"來源盲區：{m['uncovered_domains_in_source_audit'] if m['uncovered_domains_in_source_audit'] is not None else '尚未診斷'} 個觀測領域缺乏發布機構。\n",
       '**尚未建立的能力：** 重要性評分、真正跨媒體查證、新聞遺漏率測量、每日中文深度摘要；未經驗證不可宣稱已有這些能力。\n']
 text='\n'.join(lines)
 print(text)
 summary=os.getenv('GITHUB_STEP_SUMMARY')
 if summary:
  with open(summary,'a',encoding='utf-8') as f:f.write(text)
if __name__=='__main__':main()
