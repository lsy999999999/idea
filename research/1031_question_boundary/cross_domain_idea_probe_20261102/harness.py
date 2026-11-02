"""Fixed cross-domain idea test transport; no organizer scientific proposals."""
import argparse
import ast
import datetime as dt
import hashlib
import html
import json
import re
import subprocess
import sys
import urllib.parse
from pathlib import Path

ROOT=Path(__file__).resolve().parent
METHODS=ROOT.parent/'leader_methods_v1_20261102'
PYTHON='/Applications/deep_learning_hm/.venv/bin/python'
ORDER=['L1','R1','L2']

def now():return dt.datetime.now(dt.timezone.utc).isoformat()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def dump(p,obj):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x') as f:f.write(obj if isinstance(obj,str) else json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False))
def event(run,kind,**kw):
    with (run/'events.jsonl').open('a') as f:f.write(json.dumps(dict(time=now(),kind=kind,**kw),ensure_ascii=False)+'\n')
def state(run):return read(sorted((run/'states').glob('*.json'))[-1])
def save(run,s,reason):
    s['version']+=1;dump(run/'states'/f"{s['version']:04d}.json",s);event(run,'state',version=s['version'],reason=reason)
    return s

def prepare():
    import pandas as pd
    import numpy as np
    cases=read(ROOT/'CASES.json')
    docs=[]
    for case in cases:
        uid=case['uci_id'];data=ROOT/'sources'/f'uci_{uid}_data.csv';meta=ROOT/'sources'/f'uci_{uid}_metadata.json'
        assert data.exists() and meta.exists(),uid
        df=pd.read_csv(data);metadata=read(meta)['data']
        stats={}
        for col in df:
            series=df[col]
            row=dict(dtype=str(series.dtype),missing=int(series.isna().sum()),unique=int(series.nunique()))
            if pd.api.types.is_numeric_dtype(series):
                row['quantiles']={str(k):float(v) for k,v in series.quantile([0,.25,.5,.75,1]).items() if pd.notna(v)}
            else:row['top_values']={str(k):int(v) for k,v in series.value_counts().head(8).items()}
            stats[col]=row
        sample=json.loads(df.iloc[np.linspace(0,len(df)-1,min(8,len(df)),dtype=int)].to_json(orient='records'))
        core=dict(case=case,official_documentation=metadata,data_profile=dict(actual_rows=len(df),official_reported_instances=metadata['num_instances'],column_names=list(df.columns),univariate_stats=stats,fixed_sample_rows=sample,row_count_note='Actual parsed row count governs computation; metadata discrepancy retained.'),data_sha256=sha(data),metadata_sha256=sha(meta),method_index=(METHODS/'METHOD_INDEX.md').read_text())
        dump(ROOT/'cases'/f"{case['id']}.json",core)
        docs.append(dict(case_id=case['id'],uci_id=uid,rows=len(df),official_rows=metadata['num_instances'],data_sha256=sha(data),metadata_sha256=sha(meta),core_sha256=sha(ROOT/'cases'/f"{case['id']}.json")))
        for rep in [1,2]:
            rid=f"{case['id']}_{rep}";run=ROOT/'runs'/rid
            for d in ['states','inputs','replies','sealed_replies','finished','tools']:(run/d).mkdir(parents=True,exist_ok=False)
            dump(run/'config.json',dict(run_id=rid,case_id=case['id'],replicate=rep,model_requested='gpt-6-luna',reply_cap=3,compute_cap=1,search_cap=1,core_path=str(ROOT/'cases'/f"{case['id']}.json"),core_sha256=sha(ROOT/'cases'/f"{case['id']}.json"),data_path=str(data),data_sha256=sha(data)))
            save(run,dict(version=-1,replies=[],tools=[],counters=dict(replies=0,compute=0,search=0),final=None),'initial')
    dump(ROOT/'DATA_MANIFEST.json',dict(time=now(),cases=docs,sources='UCI public API and its declared CSV URLs',scope='Univariate descriptions only; no organizer pairwise scientific relationship supplied'))
    dump(ROOT/'FROZEN_DESIGN.json',dict(time=now(),protocol_sha256=sha(ROOT/'PROTOCOL.md'),role_sha256=sha(ROOT/'ROLE.md'),harness_sha256=sha(Path(__file__)),cases_sha256=sha(ROOT/'CASES.json'),data_manifest_sha256=sha(ROOT/'DATA_MANIFEST.json'),original_role_hashes={n:sha(METHODS/n) for n in ['LEADER_SYSTEM_PROMPT.md','RESEARCHER_SYSTEM_PROMPT.md','METHOD_INDEX.md','METHOD_LIBRARY.json']},cases=12,domains=6,role_calls=36,scope='Frozen before any research output'))
    print(json.dumps(docs,ensure_ascii=False))

def make_input(rid):
    run=ROOT/'runs'/rid;cfg=read(run/'config.json');s=state(run);label=ORDER[s['counters']['replies']]
    assert not any(t['result']['status']=='waiting_external' for t in s['tools'])
    role='executor' if label=='R1' else 'leader'
    library={c['id']:c for c in read(METHODS/'METHOD_LIBRARY.json')['cards']}
    selected=s['replies'][0]['reply'].get('method_ids',[])[:3] if s['replies'] else []
    bundle=dict(run_id=rid,role=role,label=label,final_turn=label=='L2',instruction=(ROOT/'ROLE.md').read_text(),original_role_principles=(METHODS/('RESEARCHER_SYSTEM_PROMPT.md' if role=='executor' else 'LEADER_SYSTEM_PROMPT.md')).read_text(),task_goal_override='This run evaluates specific idea generation, not complete mechanism discovery. Apply original principles at this stage; final scientific truth is not the acceptance target.',materials=read(Path(cfg['core_path'])),method_cards=[library[i] for i in selected if i in library],state=s,remaining=dict(role_replies=3-s['counters']['replies'],compute=1-s['counters']['compute'],search=1-s['counters']['search']),output_file=str(run/'replies'/f'{label}.json'),tool_data='DF is the complete raw public CSV as pandas DataFrame, exact columns in profile; TABLES[main]=DF. Actual counts and data hashes verified.',isolation='Read only this bundle; other cases, memory, network and direct scientific execution prohibited by protocol, not OS sandbox')
    p=run/'inputs'/f'{label}.json';dump(p,bundle)
    prompt=f"Act as cross-domain research {role.upper()}, requested gpt-6-luna. Read ONLY {p}. Inspect complete evidence and state without silently truncating. Follow the task goal and JSON schema. Write one complete JSON reply to {run/'replies'/f'{label}.json'}. Use exec only to read input/write reply and validate JSON/Python syntax; no direct scientific execution, memory, network, other files or delegation. Finish writing once, then return a completion notification."
    dump(run/'inputs'/f'{label}_dispatch.json',dict(label=label,role=role,input_path=str(p),input_sha256=sha(p),prompt=prompt,time=now()))
    event(run,'input_frozen',label=label,sha256=sha(p));print(prompt)

def compute(run,cfg,req):
    base=run/'tools'/req['id'];base.mkdir()
    code=req.get('code','');dump(base/'submitted.py',code)
    result=dict(status='clarification',code_sha256=sha(base/'submitted.py'),data_sha256=cfg['data_sha256'])
    try:
        if not code or not req.get('model_spec'):raise ValueError('Complete code and model_spec required')
        tree=ast.parse(code)
        allowed={'json','math','statistics','itertools','functools','collections','datetime','numpy','pandas','scipy','sklearn'}
        for node in ast.walk(tree):
            if isinstance(node,(ast.Import,ast.ImportFrom)):
                names=[n.name for n in node.names] if isinstance(node,ast.Import) else [node.module or '']
                if any(n.split('.')[0] not in allowed for n in names):raise ValueError('Undeclared import')
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id in {'open','exec','eval','compile','__import__','input'}:raise ValueError('External I/O/dynamic execution prohibited')
            if isinstance(node,ast.Attribute) and (node.attr.startswith('__') or node.attr.startswith('read_') or node.attr in {'to_csv','to_json','to_pickle','to_parquet','save','load','fromfile','tofile','system','popen'}):raise ValueError('External I/O prohibited; print JSON results instead')
        bootstrap='import pandas as pd\nDF=pd.read_csv('+repr(cfg['data_path'])+')\nTABLES={"main":DF}\n'+code
        dump(base/'executed.py',bootstrap)
        output=subprocess.run([PYTHON,str(base/'executed.py')],cwd=base,capture_output=True,text=True,timeout=30,env={'PATH':'/opt/homebrew/bin:/usr/bin:/bin','OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','PYTHONDONTWRITEBYTECODE':'1'})
        result.update(status='executed' if output.returncode==0 else 'failed',returncode=output.returncode,stdout=output.stdout[:40000],stderr=output.stderr[:10000],stdout_truncated=len(output.stdout)>40000)
    except subprocess.TimeoutExpired as e:result.update(status='failed',reason='30s timeout',stdout=str(e.stdout),stderr=str(e.stderr))
    except Exception as e:result.update(reason=str(e))
    dump(base/'execution.json',result);return result

def search_result(run,req):
    base=run/'tools'/req['id'];raw=base/'raw.json'
    if not raw.exists():
        base.mkdir(exist_ok=True)
        transport_error=base/'transport_error.json'
        if transport_error.exists():return dict(status='failed',reason='HTTP transport failed; no scientific search response',transport=read(transport_error),transport_sha256=sha(transport_error))
        url='https://api.crossref.org/works?'+urllib.parse.urlencode(dict(query=req['query'],rows=8,select='DOI,title,published,abstract'))
        return dict(status='waiting_external',url=url,output_path=str(raw),scope='Crossref metadata; original abstracts only when present')
    try:
        data=read(raw);items=data['message']['items'];sources=[]
        for item in items:
            parts=item.get('published',{}).get('date-parts',[])
            date=parts[0] if parts else []
            if date and tuple((date+[1,1])[:3])>(2026,11,2):continue
            abstract=html.unescape(re.sub('<[^>]+>',' ',item.get('abstract','')))
            sources.append(dict(id=req['id']+'_S'+str(len(sources)+1),title=' '.join(item.get('title',[])),doi=item.get('DOI'),published_date_parts=date,original_abstract=abstract,scope='abstract and metadata' if abstract else 'title/date/DOI only; do not infer findings',query=req['query']))
        return dict(status='returned',sources=sources,raw_sha256=sha(raw),scope='Relevance-ordered Crossref index; limited coverage, no full-text or exhaustive novelty verdict')
    except Exception as e:return dict(status='failed',reason=str(e),raw_sha256=sha(raw))

def ingest(rid,label):
    run=ROOT/'runs'/rid;cfg=read(run/'config.json');s=state(run);assert label==ORDER[s['counters']['replies']]
    dispatch=read(run/'inputs'/f'{label}_dispatch.json');assert sha(Path(dispatch['input_path']))==dispatch['input_sha256']
    p=run/'replies'/f'{label}.json';reply=read(p)
    cli_completion=run/'inputs'/f'{label}_cli_completion.json'
    completion_source='Organizer observed collaboration final notification'
    if cli_completion.exists():
        finished=read(cli_completion)
        assert finished['returncode']==0 and finished['reply_json_valid']
        completion_source='Codex CLI process exit 0 and valid JSON reply; raw event stream retained'
    dump(run/'sealed_replies'/p.name,p.read_text());dump(run/'finished'/p.name,dict(time=now(),sha256=sha(p),completion_source=completion_source,runtime_harness_sha256=sha(Path(__file__))))
    s['replies'].append(dict(label=label,role=dispatch['role'],reply=reply,input_sha256=dispatch['input_sha256'],reply_sha256=sha(p)))
    s['counters']['replies']+=1
    if label=='L2':s['final']=reply.get('final')
    save(run,s,'actor completion '+label)
    for req in reply.get('requests',[]):
        if label!='R1':event(run,'request_not_executed',reason='Only executor requests run',request=req);continue
        kind=req.get('type');tid=req.get('id','')
        if kind not in {'compute','search'} or not re.fullmatch('[A-Za-z0-9_-]{1,60}',tid):raise ValueError('Invalid tool request')
        assert tid not in [t['id'] for t in s['tools']]
        if s['counters'][kind]>=1:result=dict(status='blocked',reason=kind+' budget exhausted')
        else:
            s['counters'][kind]+=1
            if kind=='compute':result=compute(run,cfg,req)
            elif not all(req.get(k) for k in ['missing_relation','query','change_if_found']):result=dict(status='clarification',reason='missing query/relation/change_if_found')
            else:result=search_result(run,req)
        record=dict(id=tid,type=kind,request=req,result=result);s['tools'].append(record);dump(run/'tools'/f'{tid}_record.json',record);save(run,s,'tool '+tid)
    print(json.dumps(dict(run=rid,label=label,counters=s['counters'],tools=[dict(id=t['id'],status=t['result']['status'],url=t['result'].get('url'),output_path=t['result'].get('output_path'),reason=t['result'].get('reason'),stderr=t['result'].get('stderr','')) for t in s['tools']],final_status=(s['final'] or {}).get('status')),ensure_ascii=False))

def finish_search(rid,tid):
    run=ROOT/'runs'/rid;s=state(run);tool=next(t for t in s['tools'] if t['id']==tid)
    assert tool['result']['status']=='waiting_external';result=search_result(run,tool['request']);assert result['status']!='waiting_external'
    tool['result']=result;dump(run/'tools'/f'{tid}_returned.json',tool);save(run,s,'external search return '+tid)
    print(json.dumps(dict(run=rid,id=tid,status=result['status'],sources=len(result.get('sources',[])))))

def pending():
    for run in sorted((ROOT/'runs').iterdir()):
        for t in state(run)['tools']:
            if t['result']['status']=='waiting_external':print(json.dumps(dict(run=run.name,id=t['id'],**t['result'])))

def freeze(rid):
    run=ROOT/'runs'/rid;s=state(run);assert s['counters']['replies']==3 and s['final'] is not None
    assert not any(t['result']['status']=='waiting_external' for t in s['tools'])
    files={str(p.relative_to(run)):sha(p) for p in sorted(run.rglob('*')) if p.is_file()}
    dump(run/'FROZEN.json',dict(time=now(),files=files,counters=s['counters']))
    print(json.dumps(dict(run=rid,sha256=sha(run/'FROZEN.json'))))

if __name__=='__main__':
    a=sys.argv[1]
    if a=='prepare':prepare()
    elif a=='input':make_input(sys.argv[2])
    elif a=='ingest':ingest(sys.argv[2],sys.argv[3])
    elif a=='finish-search':finish_search(sys.argv[2],sys.argv[3])
    elif a=='pending':pending()
    elif a=='freeze':freeze(sys.argv[2])
