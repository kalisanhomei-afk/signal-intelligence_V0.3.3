#!/usr/bin/env python3
"""Append honest source coverage diagnosis to GitHub Actions step summary."""
import argparse,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--append',required=True)
a=p.parse_args()
x=json.loads(Path(a.input).read_text(encoding='utf-8'))
m=x['meta']
body=f"""\n### SIGNAL V0.4.3｜情報來源覆蓋與盲區驗收

> 本報告衡量「已接入來源能觀察到什麼」，**不是全球重要新聞的覆蓋率、重要性排名或事實查證結果**。

- 已接入獨立發布機構：{m['observed_publishers']}
- 來源目前完全空白的觀測領域：{m['domains_no_observed_publisher']} / {len(x['dimensions'])}
- 僅一發布機構觀測的領域：{m['domains_single_publisher']}
- 人工確認的重大事件基準筆數：{m['benchmarked_event_count']}
- 全球重大事件遺漏率：**尚不可量測**
- 獨立驗證的主張：**0**

| 觀測領域 | 實際出現的不同發布機構 | 限制 |
|---|---:|---|
"""
for d in x['dimensions']:
    caption='尚無正式接入來源' if d['observed_publisher_count']==0 else '發布機構數不是主張證據數'
    body+=f"| {d['label']} | {d['observed_publisher_count']} | {caption} |\n"
body+='\n完成來源擴充與人工基準建立前，不應自動輸出「全球重大新聞」、「完整每日情報」或投資預測。\n'
with open(a.append,'a',encoding='utf-8') as f:f.write(body)
print('V0.4.3 coverage report appended')
