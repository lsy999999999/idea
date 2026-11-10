"""Register local original texts privately for on-demand neutral definition disclosure."""
import argparse,hashlib,json
from pathlib import Path
from bs4 import BeautifulSoup


def register(root,case,paths):
    folder=Path(root)/'controller_only'/case
    folder.mkdir(parents=True,exist_ok=True)
    target=folder/'registered_sources.json'
    if target.exists():raise ValueError('Registry already exists; use a new development/run copy to change sources')
    rows=[]
    for index,source in enumerate(paths):
        source=Path(source).resolve();raw=source.read_bytes();text=raw.decode('utf-8')
        if source.suffix.lower() in {'.html','.htm','.xml'}:
            soup=BeautifulSoup(text,'html.parser')
            for node in soup(['script','style','nav','header','footer']):node.decompose()
            body=soup.find('article') or soup.find('main') or soup
            text=body.get_text('\n',strip=True)
        if not text.strip():raise ValueError('Empty registered source')
        sid=f'O{index+1:03d}';path=folder/(sid+'.txt');path.write_text(text)
        raw_path=folder/(sid+'.original'+source.suffix);raw_path.write_bytes(raw)
        rows.append({'id':sid,'path':str(path.resolve()),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                     'original_path':str(raw_path.resolve()),'original_sha256':hashlib.sha256(raw).hexdigest(),
                     'origin':str(source),'extraction':'HTML/XML text extraction' if text!=raw.decode('utf-8') else 'verbatim text'})
    target.write_text(json.dumps({'documents':rows},ensure_ascii=False,indent=2))
    return {'registered_documents':len(rows),'characters':sum(len(Path(r['path']).read_text()) for r in rows)}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--case',required=True,choices=['optical','wave'])
    p.add_argument('--source',action='append',type=Path,required=True);a=p.parse_args()
    print(register(Path(__file__).resolve().parents[1],a.case,a.source))
