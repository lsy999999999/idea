import concurrent.futures as cf
import json, sys, time, urllib.request, urllib.parse
from pathlib import Path
from html.parser import HTMLParser

ROOT = Path(__file__).parent
class Text(HTMLParser):
    def __init__(self):
        super().__init__(); self.skip = 0; self.parts = []
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'): self.skip += 1
    def handle_endtag(self, tag):
        if tag in ('script', 'style'): self.skip = max(0, self.skip-1)
    def handle_data(self, data):
        if not self.skip and data.strip(): self.parts.append(data.strip())

def fetch(job):
    name, url = job
    for attempt in range(2):
        try:
            req = urllib.request.Request(url, headers={'User-Agent':'ResearchLiteratureReader/1.0'})
            with urllib.request.urlopen(req, timeout=35) as r:
                raw = r.read().decode('utf-8', errors='replace')
                final_url = r.url
            (ROOT/'sources').mkdir(exist_ok=True)
            is_json = raw.lstrip().startswith(('{', '['))
            (ROOT/'sources'/f'{name}.{"json" if is_json else "html"}').write_text(raw)
            if not is_json:
                p = Text(); p.feed(raw)
                (ROOT/'sources'/f'{name}.txt').write_text('\n'.join(p.parts))
            return {'id':name,'url':url,'final_url':final_url,'bytes':len(raw),'status':'ok'}
        except Exception as e:
            err = str(e)
    return {'id':name,'url':url,'status':'error','error':err}

if __name__ == '__main__':
    jobs = json.loads(Path(sys.argv[1]).read_text())
    with cf.ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(fetch, jobs))
    (ROOT/(Path(sys.argv[1]).stem+'_results.json')).write_text(json.dumps(results, ensure_ascii=False, indent=2))
    for r in results: print(json.dumps(r,ensure_ascii=False))
