#!/usr/bin/env python3
"""V0.5.2 runtime summary. No secrets or claim of accuracy."""
import json,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    meta=json.loads((ROOT/'data/impact_review_v052.json').read_text(encoding='utf-8'))['meta']
    lines=['\n## SIGNAL V0.5.2｜暫定人工關注順序與 AI 審閱草稿\n',
     '> **不是已查證的新聞、正式重要性分數、交易訊號或全球完整情報。** 目前只讀取已准入的標題及少量匹配 arXiv 作者摘要。\n',
     f'七日候選池：{meta["input_pool_considered"]}；展示人工審閱候選：{meta["review_count"]}；和原「每日選讀」重疊：{meta["baseline_candidate_overlap"]}。\n',
     f'AI 啟用：{"是" if meta["ai_enabled"] else "否"}；AI 條件式草稿：{meta["ai_drafts"]}；既有草稿快取：{meta["cached_ai_drafts"]}。\n',
     f'本次模型呼叫：{meta["api_calls_attempted"]}；失敗：{meta["api_failures"]}；錯誤類別：{meta["api_error_categories"]}。\n',
     f'來源過期：{"是" if meta["stale_source"] else "否"}。已獨立查證主張：0；全球重要事件召回率：未測量；AI 重要性準確率：未測量。\n',
     '此為從既有資訊中挑選「優先人工閱讀」的試行系統，不可解讀為完成跨來源查證或可用於交易決策。\n']
    s='\n'.join(lines)
    print(s)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'],'a',encoding='utf-8') as f:f.write(s)
if __name__=='__main__':main()
