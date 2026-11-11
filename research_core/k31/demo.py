from __future__ import annotations
import html
import json
from pathlib import Path
from .engine import assemble_study

HERE = Path(__file__).resolve().parent

def esc(x):
    return html.escape(str(x),quote=True)

def render(doc):
    trials=doc['trials'];comp=doc['comparison']
    tr=''.join('''<tr><td>{o}</td><td>{d}</td><td>{s}%</td><td>{delta}</td><td>{guess}</td><td>{old} → {actual}</td><td>{verdict}</td></tr>'''.format(
        o=esc(x['forecast_origin'][:10]),d=esc(x['target_release'][:10]),s=esc(x['signal_good_excellent_pct']),
        delta=esc(x['signal_selected_edition_change_pp'] if x['signal_selected_edition_change_pp'] is not None else '—'),
        guess=esc(x['mechanical_hypothesis_next_yield_revision']),old=esc(x['current_wasde_yield_bushels_per_acre']),
        actual=esc(x['next_wasde_yield_estimate_bushels_per_acre']),verdict=esc(
            '✅ 方向吻合' if x['direction_correct_if_testable'] is True else
            '✕ 方向不吻合' if x['direction_correct_if_testable'] is False else '未評估')) for x in trials)
    sources=''.join('<tr><td>{d}</td><td>{v}%</td><td><a href="{u}">官方 NASS TXT</a></td></tr>'.format(d=esc(r['source_date']),v=esc(r['good_excellent_pct']),u=esc(r['source_uri'])) for r in doc['all_lead_observations'])
    return '''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SIGNAL K3.1｜領先訊號驗收</title><style>
    :root{{--bg:#080d13;--panel:#14202d;--line:#334353;--gold:#e0bd75;--ink:#f5f0e8;--sub:#b8c5cf}}body{{background:var(--bg);color:var(--ink);font:15px/1.75 system-ui,'Microsoft JhengHei',sans-serif;max-width:1130px;padding:20px;margin:32px auto}}h1,h2{{color:var(--gold)}}.tag{{color:var(--gold);letter-spacing:3px;font-size:12px}}.lead{{font-size:18px;color:#ddd7cd}}section{{padding:26px;border:1px solid var(--line);background:var(--panel);border-radius:14px;margin:22px 0}}.warn{{background:#392d1d;border-left:3px solid #f1c96f;padding:16px;color:#f1e4c8}}.metric{{font-size:30px;font-weight:700;color:var(--gold)}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}}.box{{background:#172633;padding:18px;border-radius:11px}}.muted{{color:var(--sub)}}table{{width:100%;border-collapse:collapse;display:block;overflow-x:auto}}th,td{{border-bottom:1px solid var(--line);text-align:left;padding:12px;white-space:nowrap}}th{{color:var(--gold)}}a{{color:#f7d08c}}code{{color:#efdaab}}footer{{color:var(--sub)}}
    </style></head><body><p class="tag">視界 SIGNAL / RESEARCH ENGINE / K3.1</p><h1>美國玉米｜領先指標與預測回放</h1><p class="lead">真實 USDA NASS 作物狀況 × K3 WASDE 歷史版本，驗證「當時可用資料能否在下一次官方報告前提供方向線索」。</p>
    <div class="warn"><b>結論：尚未建立預測優勢。</b>目前只有 2026/27 單一作物年度、兩個可比較的方向案例，測的是 <b>下次 USDA 單產預估修訂方向</b>，不是已實現產量、期貨價格或交易損益。</div>
    <section><h2>實驗看板</h2><div class="grid"><div class="box"><div class="muted">具方向判定的案例</div><div class="metric">{evaluated}</div></div><div class="box"><div class="muted">方向吻合</div><div class="metric">{correct} / {evaluated}</div></div><div class="box"><div class="muted">目前能否宣稱優於基準</div><div class="metric">不能</div></div></div></section>
    <section><h2>每次凍結於當時資訊的觀測</h2><p class="muted">單產單位：蒲式耳／英畝；「G+E」為 USDA NASS 18 州作物狀況評等中的 Good＋Excellent 百分比。訊號變動指已選取兩期官方版本的差值，非每週連續變動。</p><table><thead><tr><th>預測起點</th><th>下一次 WASDE</th><th>最新 G+E</th><th>選定兩期差(百分點)</th><th>預測修訂方向</th><th>官方單產估計前→後</th><th>結果</th></tr></thead><tbody>{rows}</tbody></table></section>
    <section><h2>和既有基準的差別</h2><p>原 K3 持續性基準沿用既有 WASDE <b>期末庫存預估</b>，衡量下一次期末庫存估計修訂。K3.1 先處理與作物狀況較直接相關的<b>單產估計修訂方向</b>，兩者目前 <b>不同目標、不同指標，不能直接比較分數</b>。</p><p>這裡附列單產持續性基準（當前單產估計預測下一次單產估計）的 MAE <strong>{baseline}</strong> 蒲式耳／英畝，但訊號模型只預測方向，尚不能與它比 MAE。</p></section>
    <section><h2>資料來源與時點</h2><p>4 筆 USDA NASS 作物報告由人工逐列轉錄。由於未在資料包內保存「精確至秒的官方歷史發布時間」，本實驗採<b>次日 12:00 UTC 的保守可得時點代理值</b>；這不是官方真正的發布時分秒。</p><table><thead><tr><th>NASS 公布版</th><th>Good＋Excellent</th><th>來源</th></tr></thead><tbody>{source_rows}</tbody></table><p class="muted">只在後來重建已公開歷史資料；不代表 SIGNAL 在 2026 年 7 月就實際儲存了它。每筆仍應人工核對全文與當時公布版本。</p></section>
    <section><h2>尚未納入評分的最新觀察</h2><p>2026/10/09 起點已可使用 2026/10/05 的 NASS 版本（G+E＝54%，相對前一個選取版本下降 2 個百分點）。K3 固定資料截至 10/09，<strong>尚未加入 11/10 官方新版</strong>；本項不計入預測成績，也不宣稱它是即時新預測。</p></section><section><h2>下一階段 K3.2：真正比較預測能力</h2><p>擴充到多個市場年度與更多發布月份，使用相同發布時點機制、凍結事先制定的規則，蒐集多組獨立預測，再加入天氣、面積、作物生長與市場預期。先達到至少 24 個跨年度配對樣本，再討論方向準確率、統計顯著性、MAE 和可交易市場價值。</p><p class="warn">此報告僅供研究；未經人工查證，不得發布為已驗證情報或投資訊號。</p></section><footer>資料來源：USDA NASS Crop Progress 與 USDA WASDE 官方 ESMIS。R1～K3 原有程式未改動；本模組離線獨立運作，無付費 API。</footer></body></html>'''.format(evaluated=esc(comp['direction_tested_count']), correct=esc(comp['direction_correct_count']), rows=tr, source_rows=sources,baseline=esc(comp['baseline_mae_bu_per_acre']))

def main():
    doc=assemble_study()
    out=HERE/'out';out.mkdir(exist_ok=True)
    (out/'k31_leading_indicator_study.json').write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (out/'k31_review.html').write_text(render(doc),encoding='utf-8')
    print('K3.1: evaluated directional trials:',doc['comparison']['direction_tested_count'])
    print('K3.1: correct directional trials:',doc['comparison']['direction_correct_count'])
    print('K3.1: forecast skill established:',doc['comparison']['forecast_skill_established'])
    print('K3.1: official sources are manually transcribed, conservative public-vintage availability used.')

if __name__=='__main__':main()
