from pathlib import Path
import urllib.request, urllib.parse, json, concurrent.futures,re
ROOT=Path(__file__).resolve().parent
urls={'wave_page':'https://www.nature.com/articles/s41586-026-11163-6','wave_zenodo_search':'https://zenodo.org/api/records/?'+urllib.parse.urlencode({'q':'"Wave coarsening drives time crystallization"','size':5}),'optical_data':'https://zenodo.org/api/records/20775840','optical_code':'https://zenodo.org/api/records/20835638'}
def fetch(item):
 name,url=item
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (research reproduction)'}),timeout=30) as r: data=r.read();ctype=r.headers.get('content-type','')
  p=ROOT/(name+('.json' if 'json' in ctype else '.html'));p.write_bytes(data)
  if name=='wave_page':return {'name':name,'bytes':len(data),'data_links':sorted(set(re.findall(r'https?[^\s<>"\)]+(?:zenodo|figshare|uva|4tu)[^\s<>"\)]+',data.decode(errors='replace'))))[:30],'data_section':re.sub('<[^>]+>',' ',data.decode(errors='replace'))[re.sub('<[^>]+>',' ',data.decode(errors='replace')).find('Data availability'):][:1600]}
  d=json.loads(data)
  if name=='wave_zenodo_search':return {'name':name,'hits':[{'id':i['id'],'title':i['metadata'].get('title'),'files':[(f['key'],f['size']) for f in i.get('files',[])]} for i in d.get('hits',{}).get('hits',[])]}
  return {'name':name,'title':d['metadata']['title'],'files':[(f['key'],f['size']) for f in d.get('files',[])]}
 except Exception as e:return {'name':name,'url':url,'error':str(e)}
rows=list(concurrent.futures.ThreadPoolExecutor(max_workers=4).map(fetch,urls.items()));(ROOT/'fetch_status.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2));print(json.dumps(rows,ensure_ascii=False,indent=2))
