#!/usr/bin/env python3
"""GitHub Actions summary for V0.4.2; no claims of independent verification."""
import argparse,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--evidence',required=True);p.add_argument('--append',required=True)
a=p.parse_args()
m=json.loads(Path(a.evidence).read_text(encoding='utf-8'))['meta']
body=f'''\n### SIGNAL V0.4.2 官方作者摘要元資料補充

> M0A 表示核對到 arXiv 官方 API 的**作者摘要元資料**。這不是論文全文、獨立查證、同儕審查或重大性評分。

- 候選：{m.get('candidate_count',0)}
- M0A 作者摘要：{m.get('m0a_count',0)}
- M0 標題元資料：{m.get('m0_count',0)}
- 本次補入：{m.get('fetched_in_run',0)}
- 官方 API 問題：{len(m.get('api_errors',[]))}
- 已獨立驗證主張：**0**

若所有來源仍停留 M0，請檢視 API 連線狀態與候選的 arXiv 網址／標題是否相符；勿將工作流程綠色勾號視為內容查證成功。\n'''
with open(a.append,'a',encoding='utf-8') as out:out.write(body)
print('Published V0.4.2 evidence-enrichment status (M0A=%d, error=%d)'%(m.get('m0a_count',0),len(m.get('api_errors',[]))))
