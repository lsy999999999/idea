"""Snapshot public paper and repository evidence; never invokes research models."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import sys
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser

class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
        self.links = []
    def handle_data(self, data):
        if data.strip():
            self.text.append(data.strip())
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.links.extend(v for k, v in attrs if k == 'href' and v)

ROOT = Path(__file__).resolve().parent

def fetch(item):
    name, url = item
    row = {'name': name, 'url': url, 'retrieved_at': datetime.now(timezone.utc).isoformat()}
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Research-reproduction-source-audit/1.0'})
        with urllib.request.urlopen(req, timeout=45) as response:
            raw = response.read()
            row.update(status=response.status, final_url=response.url)
        p = ROOT / 'sources' / name
        p.write_bytes(raw)
        row.update(file=str(p.relative_to(ROOT)), sha256=hashlib.sha256(raw).hexdigest())
        if name.endswith('.html'):
            page = Page()
            page.feed(raw.decode('utf-8', errors='replace'))
            p.with_suffix('.txt').write_text('\n'.join(page.text))
            row['github_links'] = sorted(set(x for x in page.links if 'github.com/' in x))
    except Exception as exc:
        row['error'] = str(exc)
    return row

if __name__ == '__main__':
    jobs = json.loads(Path(sys.argv[1]).read_text())
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(fetch, jobs.items()))
    out = ROOT / (Path(sys.argv[1]).stem + '_manifest.json')
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    for r in results:
        print(json.dumps(r, ensure_ascii=False))
