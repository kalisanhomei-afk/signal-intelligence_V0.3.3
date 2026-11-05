"""Bundle verified editorial snapshot as offline fallback. Do not bundle live news as verified."""
import json
from pathlib import Path
p = Path(__file__).resolve().parents[1]
data = json.loads((p / 'data/feed.json').read_text(encoding='utf-8'))
html = (p / 'index.template.html').read_text(encoding='utf-8')
assert html.count('__DATA__') == 1
safe_json = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
(p / 'index.html').write_text(html.replace('__DATA__', safe_json), encoding='utf-8')
print('index.html generated with static editorial snapshot and dynamic discovery support')
