#!/usr/bin/env python3
"""Publish date-anomaly counts; never infer news date from ingestion."""
import json,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
x=json.loads((ROOT/'data/date_quality_v052a.json').read_text(encoding='utf-8'))
m=x['meta'];c=m['counts']
s=("\n## SIGNAL V0.5.2a｜來源發布日期品質\n\n"
   "> 首次採集時間不是新聞發布時間；無日期或日期超前者不得出現在「新發現」或今日候選。\n\n"
   f"保留元資料總數：{m['total_checked']}；近7天有可信時間：{c['recent_7_days']}；"
   f"較早資訊：{c['older_than_7_days']}；缺日期：{c['missing_date']}；未來日期：{c['future_date']}。\n\n"
   "後續應人工核對缺失日期，不能擅自補寫為今日；不產生重要性或可信度分數。\n")
print(s)
if os.environ.get('GITHUB_STEP_SUMMARY'):
  with open(os.environ['GITHUB_STEP_SUMMARY'],'a',encoding='utf-8') as f:f.write(s)
