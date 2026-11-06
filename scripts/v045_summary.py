#!/usr/bin/env python3
"""Metadata-only rollout and independent-newsroom licensing gate summary."""
import json,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
 cfg=json.loads((ROOT/'data/v034_sources.json').read_text(encoding='utf-8'))
 live=json.loads((ROOT/'data/live_items.json').read_text(encoding='utf-8'))
 reviews=json.loads((ROOT/'data/v045_source_review.json').read_text(encoding='utf-8'))
 from collect_v034 import checked_sources
 src=checked_sources(cfg);by={x['source_id']:x for x in live.get('sources',[])}
 assert len(src)==8 and len({x['publisher_id'] for x in src})==7
 pilots=[]
 for sid in ('eu-press','mit-research'):
  row=by.get(sid,{})
  pilots.append(f"| {sid} | {'成功' if row.get('ok') else '未成功'} | {row.get('count',0)} | {row.get('error') or '—'} |")
 lines=['\n## SIGNAL V0.4.5｜跨領域來源試運行與媒體權利門檻\n',
        '> 「來源連線成功」不等於「獨立報導、驗證成功、可自動摘要」。新增的 EC 是官方政治消息，MIT News 是機構自有新聞。\n',
        f"來源頻道設定：{len(src)}；獨立發布機構上限：{len({x['publisher_id'] for x in src})}；本次成功：{live.get('meta',{}).get('successful_sources')}/{live.get('meta',{}).get('source_count')}。\n",
        '| 本次新增來源 | 實際連線 | 讀取標題 | 錯誤 |','|---|---|---:|---|',*pilots,
        f"\n**仍未機器接入的獨立新聞機構：{len(reviews['independent_journalism_holds'])} 家。** Reuters、AP、BBC、FT、Nikkei 的 metadata／商業授權尚未確認，不能擅自抓取。\n",
        '**不可宣稱：** 全球新聞覆蓋率、重大事件遺漏率、新聞可信度總分、獨立交叉查證成功。\n']
 val='\n'.join(lines)
 summary=os.getenv('GITHUB_STEP_SUMMARY')
 if summary:
  with open(summary,'a',encoding='utf-8') as f:f.write(val)
 print(val)
if __name__=='__main__':main()
