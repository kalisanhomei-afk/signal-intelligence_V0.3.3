#!/usr/bin/env python3
"""Report simple collection health to GitHub job summary."""
import argparse, json
from pathlib import Path

def build(data):
    meta=data.get('meta',{})
    out=['# SIGNAL V0.3.4 官方／研究元資料更新', '',
         '**請注意：這是公開元資料採集，不是 AI 整理與查證後的新聞。**', '',
         f"- 採集狀態：**{meta.get('status','unknown')}**",
         f"- 嘗試時間 UTC：{meta.get('last_attempt_at') or '尚未執行'}",
         f"- 本次成功通道：**{meta.get('successful_sources',0)} / {meta.get('source_count',0)}**",
         f"- 保留標題：{meta.get('item_count',0)}",
         f"- 本次新增：{meta.get('new_items_in_run',0)}", '',
         '| 來源 | 連線 | 新讀取標題 | 錯誤 |', '|---|---|---:|---|']
    for h in data.get('sources',[]):
        error=str(h.get('error') or '—').replace('|','/')
        out.append(f"| {h.get('source_id')} | {'成功' if h.get('ok') else '失敗'} | {h.get('count',0)} | {error} |")
    out+=['', '原始連結、發布日期與出處會在 SIGNAL「新發現」頁面顯示；網站原本「今日情報」仍為有標註日期的靜態編輯樣本。',
          'arXiv 論文未必經過同儕審查；不同 RSS 頻道不算獨立發布機構。']
    return '\n'.join(out)+'\n'

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();Path(a.output).write_text(build(json.loads(Path(a.input).read_text(encoding='utf-8'))),encoding='utf-8')
