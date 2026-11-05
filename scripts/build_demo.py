"""Create a clearly labeled OFFLINE functional UI demo with fake headlines.
Never promote simulated headlines to the live discovered.json or editorial feed.
"""
from pathlib import Path
import json
p=Path(__file__).resolve().parents[1]
html=(p/'index.html').read_text(encoding='utf-8')
rows=[
 ('科技','Engineering Notes','TEST ONLY｜示範：模組化機器人技術提出新流程'),
 ('知識','Research Archive','TEST ONLY｜示範：新材料研究待驗證其工業可行性'),
 ('財經','Central Bank Example','TEST ONLY｜示範：貨幣政策研究的新進展'),
 ('產業','Industry Wire','TEST ONLY｜示範：製造供應鏈投資可能出現調整'),
 ('政治','Global Affairs Example','TEST ONLY｜示範：國際峰會對貿易政策的影響'),
 ('社會','Public Science Example','TEST ONLY｜示範：人口結構及勞動市場研究'),
 ('能源','Energy Research Example','TEST ONLY｜示範：儲能材料降本研究發布'),
 ('科技','Development Group','TEST ONLY｜示範：新的 AI Agent 工具發布'),
 ('知識','Physics Lab','TEST ONLY｜示範：新的物理研究預印本'),
 ('產業','Business Strategy Desk','TEST ONLY｜示範：企業採購平台採用新商業模式')]
items=[];health=[]
for i,(cat,source,title) in enumerate(rows):
 src=f'demo-source-{i}'
 items.append({'id':f'demo-{i}','title':title,'url':f'https://example.org/demo/{i}',
   'source':source+'（虛構）','source_id':src, 'source_kind':'demo',
   'category':cat,'published_at':f'2026-11-05T{max(0,18-i):02d}:00:00+00:00',
   'first_seen_at':'2026-11-05T08:00:00+00:00','status':'測試內容'})
 health.append({'source_id':src,'source':source+'（虛構）','category':cat,'source_kind':'demo',
 'ok':True,'count':1,'last_success_at':'2026-11-05T08:00:00+00:00','last_attempt_at':'2026-11-05T08:00:00+00:00'})
mock={'meta':{'mode':'demo','last_attempt_at':'2026-11-05T08:00:00+00:00','last_success_at':'2026-11-05T08:00:00+00:00','source_count':len(health),'successful_sources':len(health)},'items':items,'sources':health}
# insert inside same IIFE so source filters and UI are exercised with actual browser interactions
needle='navRender();render();loadGenerated();loadDiscovery();'
assert html.count(needle)==1
replace='DISCOVERY='+json.dumps(mock,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')+';navRender();render();discover();go(\'discover\');'
html=html.replace(needle,replace)
html=html.replace('<title>視界 SIGNAL · 個人情報系統 V0.3</title>','<title>【虛構測試】視界 SIGNAL V0.3</title>')
html=html.replace('V0.3 · 公開來源發現引擎 · 2026.11.05','DEMO · 虛構資料 · 非即時新聞')
html=html.replace('編輯精選為靜態樣本','DEMO — 此頁全部新發現都是虛構內容')
(p/'demo.html').write_text(html,encoding='utf-8')
print('demo.html generated, fictitious headings only')
