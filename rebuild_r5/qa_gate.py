#!/usr/bin/env python3
"""SIGNAL Evidence Rebuild R5: fully offline, pinned-source preflight gate.

No OpenAI, no network, no publishing. Does not modify R1-R4.
This is a *fixed archived sample* test, not a general web-news fact checker.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

GATE_VERSION = "signal-evidence-preflight-r5"
MAX_SELECTION_BYTES = 65_536
# SHA256 is calculated after normalizing CRLF to LF for Windows / Unix parity.
PINNED_FILES = {
    'rebuild_r1/fixtures/bea_e7.json': 'daca60a19a255adb5c1d24a42a4bf520586b34e018e62b8559534c3adb755bb3',
    'rebuild_r2/fixtures/eia_yields_e2_e5.json': '771ebc6739a4c55e4ad1b5260e83228c4756d198657d0a0fea607d737a7a50af',
    'rebuild_r3/fixtures/arxiv_mesa_abstract_e1_e6.json': '66f510adac22653e9e6c494fda1568761afda9d006518498e7f3b7081439ef16',
    'rebuild_r1/fact_pipeline.py': '22a2192883c93e8640813077619607c4128b5a2a0d36c9e201735848522929bf',
    'rebuild_r2/eia_pipeline.py': '5fc399de6e42ba4409aceed7a811693d6f6dbe041076b683401961fc815c8bad',
    'rebuild_r3/arxiv_pipeline.py': 'e113889f305b56fdb4c38215107c223046e6d8bcb8ec660a65fe089f1ff44d64',
    'rebuild_r4/binding_pipeline.py': '7b4c9fe57abdcc3480e30d246333d096f8da86ea9e21e77afac87ac7d904a8ca',
    'rebuild_r4/fixtures/mock_ai_selection.json': 'cee6d8b98175a96fb749941321b774bc01130ead28dceb1a37bff64dfdb83344',
}


class PreflightError(ValueError):
    """Fail-closed preflight exception, never a permissive fallback."""


def normalized_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def check_pins(root: Path) -> dict[str, str]:
    if not root.is_dir():
        raise PreflightError('repository_root_missing')
    hashes = {}
    for name, expected in PINNED_FILES.items():
        path = root / name
        if not path.is_file():
            raise PreflightError(f'archived_source_missing: {name}')
        actual = normalized_digest(path)
        hashes[name] = actual
        if expected is not None and expected != actual:
            raise PreflightError(f'archived_source_drift_detected: {name}')
    return hashes


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise PreflightError('duplicate_json_key')
        result[key] = value
    return result


def parse_selection(raw: bytes | str) -> dict:
    if isinstance(raw, str):
        raw = raw.encode('utf-8')
    if not isinstance(raw, bytes) or len(raw) > MAX_SELECTION_BYTES:
        raise PreflightError('selection_size_or_type_invalid')
    try:
        doc = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=_no_duplicate_keys,
                         parse_constant=lambda s: (_ for _ in ()).throw(PreflightError('invalid_nonfinite_json')))
    except PreflightError:
        raise
    except (ValueError, UnicodeError) as ex:
        raise PreflightError('selection_json_invalid') from ex
    if not isinstance(doc, dict):
        raise PreflightError('selection_not_object')
    return doc


def _load_r4(root: Path):
    path = root / 'rebuild_r4' / 'binding_pipeline.py'
    spec = importlib.util.spec_from_file_location('signal_r5_pinned_r4', path)
    if spec is None or spec.loader is None:
        raise PreflightError('r4_module_unavailable')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_case(root: Path, input_bytes: bytes) -> tuple[dict, dict, str]:
    """No catch-and-continue: invalid or dangerous responses produce no report."""
    check_pins(root)
    selection = parse_selection(input_bytes)
    r4 = _load_r4(root)
    try:
        bundles = r4.load_verified_bundles(root)
        catalog = r4.standard_facts(bundles)
        r4.validate_model_selection(selection, catalog)
        review = r4.build_review(bundles, selection)
        rendered = r4.render_review(review)
    except Exception as ex:
        raise PreflightError(f'model_selection_or_binding_rejected:{type(ex).__name__}') from ex
    if set(catalog) != {'bea', 'eia', 'arxiv'}:
        raise PreflightError('unexpected_source_set')
    if {k: len(v) for k, v in catalog.items()} != {'bea': 6, 'eia': 4, 'arxiv': 6}:
        raise PreflightError('unexpected_fact_count')
    if not (review.get('publication_allowed') is False and
            review.get('human_approved') is False and
            review.get('api_calls') == 0 and
            review.get('independently_verified_claims') == 0):
        raise PreflightError('unsafe_approval_or_api_status')
    if not all(c.get('model_generated_numerical_claims') == 0 for c in review['cases']):
        raise PreflightError('model_generated_number_detected')
    if any(f.get('independently_verified') is not False for subset in catalog.values() for f in subset.values()):
        raise PreflightError('unapproved_fact_status')
    if re.search(r'<script\b|javascript:', rendered, re.I):
        raise PreflightError('active_script_in_report')
    return catalog, review, rendered


def _canonical(obj: object) -> bytes:
    return (json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(',', ':')) + '\n').encode('utf-8')


def run_legacy_tests(root: Path) -> list[dict]:
    results = []
    for index, (name, count) in enumerate([('rebuild_r1',9), ('rebuild_r2',11),
                                           ('rebuild_r3',17), ('rebuild_r4',22),
                                           ('rebuild_r5',0)]):
        proc = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', name,
                               '-p', 'test_*.py', '-v'], cwd=root, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace', timeout=40)
        match = re.search(r'Ran (\d+) tests? in ', proc.stdout)
        actual_count = int(match.group(1)) if match else 0
        passed = proc.returncode == 0 and actual_count >= (count or 1) and '\nOK\n' in proc.stdout
        results.append({'suite': name.upper(), 'tests_run': actual_count,
                        'status': 'PASS' if passed else 'FAIL',
                        'tail': '\n'.join(proc.stdout.splitlines()[-9:])[-1800:]})
    return results


def qa_html(report: dict) -> str:
    esc = lambda x: html.escape(str(x), quote=True)
    rows = ''.join(f'<tr><td>{esc(r["suite"])}</td><td>{r["tests_run"]}</td><td class="{esc(r["status"])}">{esc(r["status"])}</td></tr>'
                   for r in report['suites'])
    result = esc(report['decision'])
    return f'''<!DOCTYPE html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SIGNAL R5｜離線驗收關卡</title><style>
body{{margin:auto;max-width:920px;padding:28px;background:#111923;color:#f4efe4;font:15px/1.8 system-ui,'Microsoft JhengHei',sans-serif}}
section{{background:#202c3a;border:1px solid #4c5a69;border-radius:12px;padding:22px;margin:18px 0}}h1,h2{{color:#d8b872}}table{{border-collapse:collapse;width:100%}}td,th{{border-bottom:1px solid #52606f;padding:10px;text-align:left}}th{{color:#d8b872}}.PASS{{color:#a5f0bb}}.FAIL{{color:#ff9696}}.notice{{border-left:4px solid #e3aa62;padding:12px;background:#493824}}code{{color:#ead6a6}}@media print{{body{{background:white;color:black}}section{{background:white;color:black}}}}</style></head><body>
<h1>視界 SIGNAL｜Evidence Rebuild R5</h1><p class="notice"><strong>開發階段 / 不可發布</strong>。本報告僅驗證固定的三份離線摘錄及 R4 模擬模型輸出；未執行 OpenAI API、未重新訪問官方網站，也不能證明分析品質或來源真實性。</p>
<section><h2>驗收決策：{result}</h2><p>測試總數：{esc(report['total_tests'])}；來源案例：BEA／EIA／arXiv；結構化待審事實：{esc(report['fact_count'])}；模型產生事實數字：0；付費 API：0。</p><table><tr><th>測試區</th><th>測試數</th><th>結果</th></tr>{rows}</table></section>
<section><h2>本次核對</h2><p>固定來源快照 SHA256、資料漂移攔截、錯誤輸出契約、跨來源引用、JSON 畸形與重複欄位、數值注入、報告防越權、重播一致性。詳細結果見 <code>qa_result.json</code>。</p><p>重播結果：<strong>{esc(report['replay_status'])}</strong>；完整性檢查：<strong>{esc(report['pinned_status'])}</strong>。</p></section>
<section><h2>R6 放行條件</h2><p>只有 <code>decision = OFFLINE_PASS_R6_CANDIDATE</code>，才能準備 R6 的單則付費 API 測試；這並<strong>不表示</strong>已經完成 R6/R7，更不代表可以自動發佈至正式網站。</p><p>下一步：先設計模型只選擇 ID／封閉主題的回覆介面，進行一次真實 API 冒煙測試；若內容品質不足，不得直接擴大至每日情報。</p></section>
</body></html>'''


def run_gate(root: Path, out: Path) -> dict:
    root = root.resolve()
    issues = []
    pins = {}
    try:
        pins = check_pins(root)
        pinned = 'PASS'
    except Exception as ex:
        pinned = 'FAIL'
        issues.append(str(ex))
    replay_status = 'NOT_RUN'
    count = 0
    if pinned == 'PASS':
        try:
            raw = (root / 'rebuild_r4' / 'fixtures' / 'mock_ai_selection.json').read_bytes()
            _, first, h1 = run_case(root, raw)
            _, second, h2 = run_case(root, raw)
            if _canonical(first) != _canonical(second) or h1 != h2:
                raise PreflightError('deterministic_replay_mismatch')
            count = first['catalog_fact_count']
            replay_status = 'PASS'
        except Exception as ex:
            issues.append(str(ex))
            replay_status = 'FAIL'
    suites = run_legacy_tests(root) if pinned == 'PASS' else []
    if any(s['status'] != 'PASS' for s in suites):
        issues.append('unittest_suite_failed')
    status = 'OFFLINE_PASS_R6_CANDIDATE' if not issues and len(suites)==5 else 'BLOCKED_NO_R6'
    result = {
        'gate_version':GATE_VERSION,
        'decision':status, 'pinned_status':pinned, 'replay_status':replay_status,
        'run_mode':'offline_only', 'api_calls':0,'publication_allowed':False,
        'human_approved':False,'independently_verified_claims':0,
        'fact_count':count, 'source_cases':['bea','eia','arxiv'],
        'total_tests':sum(s['tests_run'] for s in suites),
        'suites':suites, 'source_pins_sha256':pins,
        'issues':issues,
        'limits':['Pinned archive test only, not all future source formats',
                  'No real model, no remote official page read and no independent corroboration',
                  'R6 API run and R7 human review are still necessary',
                  'Not permission to publish, trade, or merge into main'],
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / 'qa_result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (out / 'qa_review.html').write_text(qa_html(result),encoding='utf-8')
    return result


def main():
    p=argparse.ArgumentParser(description='SIGNAL R5 fail-closed offline QA gate; no API/network or publish')
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parent.parent)
    p.add_argument('--out',type=Path,default=Path(__file__).resolve().parent / 'out')
    args=p.parse_args()
    result=run_gate(args.root,args.out)
    print(f'{result["decision"]}: {result["total_tests"]} tests; replay={result["replay_status"]}; sources={result["pinned_status"]}; API calls=0')
    if result['decision'] != 'OFFLINE_PASS_R6_CANDIDATE':
        print('BLOCKED:', '; '.join(result['issues']),file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
