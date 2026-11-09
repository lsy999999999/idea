from pathlib import Path
import urllib.request,json,hashlib,zipfile,concurrent.futures
ROOT=Path(__file__).resolve().parent
jobs=[('optical',20775840,['README.txt','Figure2.zip','Figure3.zip']),('wave',22541069,['FIG2.zip','simulation.zip','environment.yml'])]
def run(job):
 name,rid,files=job
 with urllib.request.urlopen(f'https://zenodo.org/api/records/{rid}',timeout=30) as r:meta=json.load(r)
 (ROOT/(name+'_metadata.json')).write_text(json.dumps(meta,ensure_ascii=False,indent=2));out=ROOT/'raw'/name;out.mkdir(parents=True,exist_ok=True);rows=[]
 for f in meta['files']:
  if f['key'] not in files:continue
  p=out/f['key']
  if not p.exists():
   with urllib.request.urlopen(f['links']['self'],timeout=90) as r:p.write_bytes(r.read())
  algorithm,expected=f['checksum'].split(':');actual=hashlib.new(algorithm,p.read_bytes()).hexdigest();assert actual==expected,p
  row={'name':f['key'],'bytes':p.stat().st_size,'checksum':f['checksum'],'url':f['links']['self']}
  if p.suffix=='.zip':
   with zipfile.ZipFile(p) as z:
    row['contents']=[{'name':i.filename,'bytes':i.file_size} for i in z.infolist()]
    if sum(i.file_size for i in z.infolist())>300000000:raise ValueError('Unexpected expanded archive size')
    target=out/p.stem;target.mkdir(exist_ok=True)
    for i in z.infolist():
     if not (target/i.filename).resolve().is_relative_to(target.resolve()):raise ValueError('Unsafe zip path')
    z.extractall(target)
  rows.append(row)
 (ROOT/(name+'_downloads.json')).write_text(json.dumps(rows,ensure_ascii=False,indent=2));return {'case':name,'files':rows}
for result in concurrent.futures.ThreadPoolExecutor(max_workers=2).map(run,jobs):print(json.dumps(result,ensure_ascii=False))
