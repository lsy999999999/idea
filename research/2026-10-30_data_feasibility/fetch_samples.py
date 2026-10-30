import concurrent.futures as cf
import datetime, hashlib, json, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
def fetch(job):
    name,url=job
    for attempt in range(2):
        try:
            req=urllib.request.Request(url,headers={'User-Agent':'AcademicResearchPrototype/0.1','Accept':'application/json,text/html,text/plain,*/*'})
            with urllib.request.urlopen(req,timeout=30) as response:
                data=response.read(40_000_001)
                if len(data)>40_000_000: raise ValueError('Sample exceeds 40 MB limit')
                content_type=response.headers.get('Content-Type','')
                final_url=response.url
            path=ROOT/'samples'/name
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(data)
            return dict(name=name,url=url,final_url=final_url,status='downloaded',bytes=len(data),
                        content_type=content_type,sha256=hashlib.sha256(data).hexdigest(),
                        fetched_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
        except Exception as e:
            error=str(e)
    return dict(name=name,url=url,status='failed',error=error)

if __name__=='__main__':
    jobs=json.loads(Path(sys.argv[1]).read_text())
    with cf.ThreadPoolExecutor(max_workers=3) as pool:
        results=list(pool.map(fetch,jobs))
    target=ROOT/(Path(sys.argv[1]).stem+'_results.json')
    target.write_text(json.dumps(results,ensure_ascii=False,indent=2))
    for r in results: print(json.dumps(r,ensure_ascii=False))
