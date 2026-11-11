'''Reproducible K3 case study: 4 published WASDE 2026 vintages.'''
from pathlib import Path
import json,html
from .engine import load_fixture,ordered_releases,component_attribution,persistence_benchmark

def render_report(doc,states,revisions,benchmark)->str:
    esc=lambda x:html.escape(str(x))
    rows=''.join('<tr><td>'+esc(x['publication'][:10])+'</td><td>'+esc(x['values']['beginning_stocks'])+'</td><td>'+esc(x['values']['production'])+'</td><td>'+esc(x['values']['domestic_use'])+'</td><td>'+esc(x['values']['exports'])+'</td><td><strong>'+esc(x['values']['ending_stocks'])+'</strong></td><td><a href="'+esc(x['source_uri'])+'">USDA 原文</a></td></tr>' for x in states)
    rrows=''.join('<tr><td>'+esc(x['old_release'][:10])+' → '+esc(x['new_release'][:10])+'</td><td>'+esc(x['stock_revision'])+'</td><td>'+esc(x['accounting_contributions'])+'</td></tr>' for x in revisions)
    frows=''.join('<tr><td>'+esc(x['frozen_as_of'][:10])+'</td><td>'+esc(x['target_release'][:10])+'</td><td>'+esc(x['predicted'])+'</td><td>'+esc(x['next_official_estimate'])+'</td><td>'+esc(x['error_actual_minus_predicted'])+'</td></tr>' for x in benchmark['forecasts'])
    return f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SIGNAL K3｜USDA 歷史發布時間回放</title><style>
    :root{{--bg:#080b12;--panel:#111a26;--line:#3b4349;--gold:#d8b76a;--text:#eee9df;--muted:#b0bdc7}}
    body{{background:var(--bg);color:var(--text);font:16px/1.7 system-ui,sans-serif;max-width:1160px;margin:40px auto;padding:0 24px}}h1,h2{{color:var(--gold)}}h1{{font-size:31px}}.intro{{color:var(--muted)}}section{{background:var(--panel);border:1px solid #4d4331;border-radius:15px;padding:22px;margin:20px 0}}table{{border-collapse:collapse;width:100%;font-size:14px;display:block;overflow-x:auto}}th,td{{border-bottom:1px solid var(--line);padding:10px;text-align:left;white-space:nowrap}}th{{color:var(--gold)}}a{{color:#e8cb8d}}.tag{{display:inline-block;padding:3px 11px;background:#372a1a;color:#f7cc78;border-radius:18px}}.metric{{font-size:29px;color:var(--gold);font-weight:bold}}.warn{{background:#2b241d;padding:13px 17px;border-left:4px solid var(--gold)}}.mono{{font-family:monospace;font-size:13px;white-space:pre-wrap}}</style></head><body>
    <p class="tag">SIGNAL / K3 / REAL USDA HISTORICAL VINTAGES</p><h1>美國玉米｜官方歷史發布回放</h1>
    <p class="intro">同一年度（2026/27）玉米供需估計，依 2026 年 7–10 月四次 USDA WASDE 的原始發布逐次保存；非現在的最終實現值。</p>
    <div class="warn"><strong>研究分層：</strong>官方發布的「預測數據」≠ 收成的「最終實現」≠ 投資市場的「交易預測」。此分析只做歷史公布時點回放、供需會計變動拆解和最簡單的基準預測。</div>
    <section><h2>一｜四次正式公告中的供需估計</h2><p>單位均為 <strong>百萬蒲式耳（million bushels）</strong>；表中「期末庫存」為該次報告對 2026/27 市場年度的預估。</p>
    <table><thead><tr><th>發布日期</th><th>期初庫存</th><th>產量預估</th><th>國內使用</th><th>出口</th><th>期末庫存預估</th><th>原始報告</th></tr></thead><tbody>{rows}</tbody></table></section>
    <section><h2>二｜反向拆解：為什麼官方估計改變？</h2><p>只能拆解帳面貢獻。真正的上游原因（天候、面積、單產及新資料）需要更多獨立證據。</p>
    <table><thead><tr><th>期間</th><th>期末庫存估計修訂</th><th>供需會計貢獻（百萬蒲式耳）</th></tr></thead><tbody>{rrows}</tbody></table></section>
    <section><h2>三｜最簡單預測基準：沿用上一期 USDA 數值</h2><p>每次發布後凍結當時估計，預測下一次 WASDE 公布時的同年度期末庫存估計。<strong>評估目標是官方估計修訂，不是玉米現貨或期貨價格。</strong></p>
    <p class="metric">MAE {esc(round(float(benchmark['mae_million_bushels']),2))} <small style="font-size:14px">百萬蒲式耳</small></p><p class="intro">僅 {len(benchmark['forecasts'])} 次相鄰發布比較，完全不足以評估穩定預測能力。</p>
    <table><thead><tr><th>預測凍結</th><th>下一次公告</th><th>基準預測</th><th>官方新估計</th><th>誤差：實際－預測</th></tr></thead><tbody>{frows}</tbody></table></section>
    <section><h2>四｜發布時間與補登時間不同</h2><p>本資料在後來研究時重建公開歷史發布版本。它允許 <code>public_replay</code> 比較『當時公開可得』的資料，但不能假裝 SIGNAL 在 7 月就已下載。</p><p>回補匯入時刻：<span class="mono">{esc(doc['archive_retrieval_utc'])}</span></p>
    <p>程式另設 <code>system_replay</code>，要求資料確實已在當時由 SIGNAL 取得；未達條件會拒絕回放。</p></section>
    <section><h2>五｜K3 結論與下一道實驗</h2><p>已建立 <strong>真實、多期、具發布時點的歷史 USDA 版本</strong>，並完成帳面校驗；尚未建立優於基準的預測模型，也沒有期貨報酬或市場預期資料。</p><p>下一階段應增加跨年度、跨年份樣本，先定義一個真正的領先訊號模型，與 persistence / USDA 共識基準作不偷看未來的比較。</p></section>
    <footer class="intro">USDA ESMIS 原始 WASDE TXT 為來源。表格摘錄為人工轉錄，請以完整官方公告為最終核對依據；本地 SHA-256 僅涵蓋摘錄，並非官方原始檔案簽章。</footer></body></html>'''

def main():
    here=Path(__file__).resolve().parent
    doc=load_fixture()
    states=ordered_releases(doc)
    rev=[component_attribution(a,b) for a,b in zip(states[:-1],states[1:])]
    bm=persistence_benchmark(states)
    out=here/'out';out.mkdir(exist_ok=True)
    data={'schema_version':'signal-k3-official-vintage-replay-v1',
          'data_provenance':'USDA ESMIS public release TXT; manual row transcription',
          'release_states':states,'revisions':rev,'benchmark':bm,
          'independently_verified_claims':0,'investment_signal':False,
          'forecast_skill_established':False,'publication_allowed':False}
    (out/'k3_release_replay.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (out/'k3_review.html').write_text(render_report(doc,states,rev,bm),encoding='utf-8')
    print('K3 real WASDE archive case:',len(states),'release vintages;',bm['sample_count'],'one-step benchmark evaluations')
    print('MAE next-release ending-stocks revisions (million bushels):',bm['mae_million_bushels'])
    print('K3 prohibits investment-signal claims and requires further historical validation.')
if __name__=='__main__':main()
