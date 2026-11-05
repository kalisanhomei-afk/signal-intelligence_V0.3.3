#!/usr/bin/env python3
"""SIGNAL V0.4.1 — provenance and evidence-gap ledger.

This generates a PUBLIC review queue, NOT factual verification. It does not fetch
article text, elevate source corroboration, or make judgments about truth.
"""
from __future__ import annotations
import argparse, datetime as dt, hashlib, json, os, tempfile
from pathlib import Path
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
RIGHTS='descriptive_public_metadata_only'
PUBLISHERS={
 'fed': {'host':'federalreserve.gov','role':'第一手政策機構','evidence_kind':'官方發布元資料',
         'questions':['是否核對原始聲明／會議紀錄全文？','是否區分決策日期、發布時間與市場預期？','是否有獨立報導確認關鍵細節？']},
 'bea': {'host':'bea.gov','role':'第一手統計機構','evidence_kind':'官方統計發布元資料',
         'questions':['是否核對官方表格、統計期間與數值？','是首次估計還是修正值？是否有後續更正？','有沒有可信的獨立解讀及不同假設？']},
 'arxiv': {'host':'arxiv.org','role':'研究預印本儲存平台','evidence_kind':'未確認同儕審查之預印本元資料',
         'questions':['是否閱讀摘要或論文、確認研究方法與樣本？','是否已通過同儕審查或有獨立重現結果？','有沒有實際部署、效能基準及限制證據？']},
}
SOURCE_TO_PUB={'fed-monetary':'fed','bea-news':'bea','arxiv-ai':'arxiv','arxiv-robotics':'arxiv'}

def load(path,default):
    path=Path(path)
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default

def write(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=path.parent,delete=False) as f:
        json.dump(data,f,indent=2,ensure_ascii=False);f.write('\n');tmp=f.name
    os.replace(tmp,path)

def _valid_host(host,root):
    return host==root or host.endswith('.'+root)

def build(articles,triage,*,now=None):
    if articles.get('meta',{}).get('mode')!='official_metadata' or articles.get('meta',{}).get('rights_scope')!=RIGHTS:
        raise ValueError('Input articles are not reviewed official metadata')
    if triage.get('meta',{}).get('rights_scope')!=RIGHTS:
        raise ValueError('Unreviewed triage input')
    known={x['id']:x for x in articles.get('items',[]) if isinstance(x,dict) and x.get('id')}
    out=[];seen=set()
    for x in triage.get('items',[]):
        if not isinstance(x,dict) or x.get('id') in seen:continue
        sid=x.get('source_id');pub=SOURCE_TO_PUB.get(sid)
        original=known.get(x.get('id'))
        if not pub or not original or pub!=x.get('publisher_id') or original.get('publisher_id')!=pub or original.get('source_id')!=sid:
            continue
        url=x.get('url','')
        u=urlsplit(url)
        if not (u.scheme=='https' and not u.username and not u.password and
                u.hostname and _valid_host(u.hostname,PUBLISHERS[pub]['host']) and
                url==original.get('url') and x.get('title')==original.get('title') and original.get('summary') is None):
            continue
        if x.get('verification_status')!='待人工核對' or x.get('independent_confirmation') is not False:
            raise ValueError('Source candidate unlawfully promoted to verified')
        seen.add(x['id']);p=PUBLISHERS[pub]
        out.append({
          'id':x['id'],'source_id':sid,'publisher_id':pub,'title':x['title'],
          'category':x.get('category','其他'),'published_at':x.get('published_at'),
          'url':url,'source_role':p['role'],'evidence_kind':p['evidence_kind'],
          'evidence_level':'M0','verification_status':'未查證','reading_scope':'僅公開標題、日期、來源連結',
          'body_read':False,'peer_review_confirmed':False,'independent_confirmation_count':0,
          'importance_assessed':False,'questions':p['questions'],
          'finding':'可以確認採集器收到該來源的公開標題元資料；主張內容與後續影響尚未驗證。',
          'fingerprint':hashlib.sha256((sid+'|'+url+'|'+x['title']).encode('utf-8')).hexdigest()[:24],
        })
    publishers=sorted({x['publisher_id'] for x in out})
    return {'meta':{
       'version':'0.4.1','generated_at':now or dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
       'rights_scope':RIGHTS,'status':'metadata_gap_audit_only',
       'candidate_count':len(out),'input_candidate_count':len(triage.get('items',[])),
       'excluded_count':len(triage.get('items',[]))-len(out),'publisher_count':len(publishers),
       'publishers':publishers,'verified_claims':0,'independently_confirmed_claims':0,
       'read_bodies':0,'importance_assessments':0,
       'coverage_warning':'來源只涵蓋 Fed、BEA 與 arXiv；重大政治、產業、其他國家／地域及多觀點尚未完整覆蓋。',
       'note':'M0 = 只有標題與來源元資料。資料進入審核清單不等於已證實、不等於全球重要性、不構成投資判斷。',
       'risk_flags':['來源覆蓋不足','未閱讀全文','缺乏獨立佐證','研究預印本未確認同儕審查']
     },'items':out}

def main(argv=None):
    ap=argparse.ArgumentParser()
    ap.add_argument('--articles',default=str(ROOT/'data/live_items.json'))
    ap.add_argument('--triage',default=str(ROOT/'data/intelligence.json'))
    ap.add_argument('--output',default=str(ROOT/'data/evidence_audit.json'))
    args=ap.parse_args(argv)
    result=build(load(args.articles,{}),load(args.triage,{}))
    write(args.output,result)
    print('V0.4.1 evidence ledger: {} metadata-only candidates / {} publishers / 0 verified'.format(result['meta']['candidate_count'],result['meta']['publisher_count']))
    return 0
if __name__=='__main__':raise SystemExit(main())
