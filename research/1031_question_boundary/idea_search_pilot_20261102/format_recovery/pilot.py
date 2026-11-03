"""Frozen, bounded model inference experiment. Never edits earlier experiments."""
import concurrent.futures as cf
import datetime as dt
import hashlib
import html
import importlib.util
import json
import os
from pathlib import Path
import random
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
PYTHON = '/Applications/deep_learning_hm/.venv/bin/python'
CLI = '/opt/homebrew/bin/codex'
METHODS = ROOT.parent / 'leader_methods_v1_20261102'
CASES = {'wine': 186, 'shopping': 468}
POLICIES = {
    'A': 'Use the common three-stage research process and the supplied full history.',
    'B': 'Use the common process and full history. Actively seek useful core directions different from prior ideas. A new name, threshold or routine subgroup is not a new direction. Same-family progress is allowed when it adds a discriminating prediction. Explain the difference from the closest prior idea.',
    'C': 'Use the common process and full history. Compare each proposal structurally with the nearest previous candidate: object, core relation/action, contrast, prediction, independent unit. Seek useful new families or genuine discriminating refinements, not cosmetic distance. Self-report the four quality gates honestly. The broker selects lexicographically by all four quality gates passed, history_relation (new_family/no_history=2, refinement=1, repeat=0), feasible_with_current_data, then lowest candidate index. Treat implementation errors, missing data, statistical uncertainty, contradicted predictions and literature overlap differently when choosing repair, measure, test, refine or explore. Never exclude an entire family solely because of one noisy or failed computation.'
}

def now(): return dt.datetime.now(dt.timezone.utc).isoformat()
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text())
def write(p, x):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('x') as f:
        f.write(x if isinstance(x, str) else json.dumps(x, ensure_ascii=False, indent=2, allow_nan=False))

def same_or_write(p, x):
    if Path(p).exists():
        assert (Path(p).read_text() == x if isinstance(x,str) else read(p)==x)
    else: write(p,x)

def effective_selection(reply, arm):
    items = reply['candidates']
    assert len(items) == 3 and [c['id'] for c in items] == ['I1', 'I2', 'I3']
    assert reply['selected_id'] in ['I1', 'I2', 'I3']
    if arm != 'C': return reply['selected_id']
    def score(c):
        gates = c['quality_gate']
        valid = all(gates.get(k) is True for k in ['specific','testable','coherent_feasible','worth_testing'])
        level = {'no_history':2,'new_family':2,'refinement':1,'repeat':0}[c['history_relation']]
        return (valid, level, c['feasible_with_current_data'] is True, -int(c['id'][1:]))
    return max(items, key=score)['id']

def prepare():
    import pandas as pd
    import numpy as np
    assert not (ROOT/'FROZEN_DESIGN.json').exists()
    for name in ['LEADER_SYSTEM_PROMPT.md','RESEARCHER_SYSTEM_PROMPT.md','METHOD_INDEX.md','METHOD_LIBRARY.json']:
        same_or_write(ROOT/'frozen_methods'/name, (METHODS/name).read_text())
    same_or_write(ROOT/'vendor_broker.py', (ROOT.parent/'cross_domain_idea_probe_20261102/harness.py').read_text())
    for case, uid in CASES.items():
        data = ROOT/'setup'/f'uci{uid}.csv'; meta = ROOT/'setup'/f'uci{uid}.json'
        df = pd.read_csv(data); doc = read(meta)['data']
        assert len(df)=={186:6497,468:12330}[uid], 'Incomplete dataset; refuse preparation'
        assert len(df.columns)=={186:13,468:18}[uid], 'Unexpected columns'
        assert not df.isna().any().any(), 'These official datasets declare no missing values; inspect mismatch'
        profile = {}
        for col in df:
            s=df[col]
            a={'dtype':str(s.dtype),'missing':int(s.isna().sum()),'unique':int(s.nunique())}
            if pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s):
                a['quantiles']={str(k):float(v) for k,v in s.quantile([0,.25,.5,.75,1]).items() if pd.notna(v)}
            else: a['top_values']={str(k):int(v) for k,v in s.value_counts().head(8).items()}
            profile[col]=a
        bundle={'case':case,'official_documentation':doc,'actual_rows':len(df),'data_sha256':sha(data),'metadata_sha256':sha(meta),
                'univariate_profile':profile,'sample_rows':json.loads(df.iloc[np.linspace(0,len(df)-1,6,dtype=int)].to_json(orient='records')),
                'task':'Find worthwhile, testable research questions beyond the supplied descriptions. All rows are available to requested computation. State data limitations and recognition; no target-paper answer is supplied.'}
        same_or_write(ROOT/'cases'/f'{case}.json', bundle)
    # Cheap policy check using fictional records, no scientific outputs.
    common={'specific':True,'testable':True,'coherent_feasible':True,'worth_testing':True}
    candidates=[{'id':f'I{i+1}','quality_gate':common,'history_relation':v,'feasible_with_current_data':True} for i,v in enumerate(['repeat','new_family','refinement'])]
    fixture={'candidates':candidates,'selected_id':'I1'}
    assert effective_selection(fixture,'A')=='I1' and effective_selection(fixture,'C')=='I2'
    same_or_write(ROOT/'setup'/'policy_check.json',{'passed':True,'scope':'Selection rule fixture, not research efficacy'})
    files=[ROOT/'PROTOCOL.md',ROOT/'ROLE.md',ROOT/'pilot.py',ROOT/'vendor_broker.py',*sorted((ROOT/'frozen_methods').glob('*')),*sorted((ROOT/'cases').glob('*')),*[ROOT/'setup'/f'uci{uid}.{ext}' for uid in CASES.values() for ext in ['json','csv']]]
    same_or_write(ROOT/'POLICIES.json',POLICIES);files.append(ROOT/'POLICIES.json')
    write(ROOT/'FROZEN_DESIGN.json',{'time':now(),'files':{str(p.relative_to(ROOT)):sha(p) for p in files},'calls':54,'review_calls':2,'cases':CASES,'arms':list(POLICIES),'rounds':3,'model_requested':'gpt-6-luna','scientific_retry_cap':0,'transport_retry_cap':1})
    print(json.dumps({'prepared':True,'cases':{c:read(ROOT/'cases'/f'{c}.json')['actual_rows'] for c in CASES}}),flush=True)

def verify_freeze():
    for p,h in read(ROOT/'FROZEN_DESIGN.json')['files'].items():
        assert sha(ROOT/p)==h, f'Frozen file modified: {p}'

def infer(path, bundle):
    path.mkdir(parents=True, exist_ok=True)
    write(path/'input.json', bundle)
    prompt='Controlled experimental model inference. Do not use any tools or access any files, memory, network or other chats. Respond directly with the requested JSON using only the following bundle.\n'+json.dumps(bundle,ensure_ascii=False)
    write(path/'prompt.txt',prompt)
    for attempt in range(2):
        out=path/f'reply_attempt{attempt}.txt'
        cmd=[CLI,'exec','--ephemeral','--skip-git-repo-check','--model','gpt-6-luna','--sandbox','read-only','--color','never','--json','--output-last-message',str(out),'-C',str(ROOT),'-']
        write(path/f'command_attempt{attempt}.json',cmd)
        start=time.monotonic()
        with (path/f'events_attempt{attempt}.jsonl').open('x') as stream, (path/f'stderr_attempt{attempt}.txt').open('x') as err:
            try:
                p=subprocess.run(cmd,input=prompt,text=True,stdout=stream,stderr=err,timeout=900)
                rc=p.returncode
            except subprocess.TimeoutExpired:
                rc=124
        usage={};violations=[]
        for line in (path/f'events_attempt{attempt}.jsonl').read_text().splitlines():
            try:e=json.loads(line)
            except json.JSONDecodeError:continue
            if e.get('type')=='turn.completed':usage=e.get('usage',{})
            item=e.get('item',{})
            if item.get('type') in ['command_execution','mcp_tool_call','web_search','file_change']:
                violations.append(item.get('type'))
        write(path/f'completion_attempt{attempt}.json',{'time':now(),'returncode':rc,'seconds':time.monotonic()-start,'usage':usage,'tool_violations':violations,'model_requested':'gpt-6-luna','model_identity_independently_verified':False})
        if violations:raise RuntimeError('Protocol violation: model used tools')
        if rc:
            if attempt==0:continue
            raise RuntimeError(f'Transport failed twice: {rc}')
        raw=out.read_text().strip()
        # Preserve formatting; allow fence wrapping without regenerating any content.
        if raw.startswith('```'):
            raw=re.sub(r'^```(?:json)?\s*','',raw);raw=re.sub(r'\s*```$','',raw)
        reply=json.loads(raw)
        assert isinstance(reply,dict)
        write(path/'reply.json',reply)
        write(path/'SEALED.json',{'time':now(),'input_sha256':sha(path/'input.json'),'reply_sha256':sha(path/'reply.json')})
        return reply

def search(base,req):
    base.mkdir(parents=True,exist_ok=True)
    url='https://api.crossref.org/works?'+urllib.parse.urlencode({'query':req['query'],'rows':6,'select':'DOI,title,published,abstract'})
    write(base/'request.json',{'url':url,'request':req,'time':now()})
    failures=[]
    for attempt in range(2):
        try:
            request=urllib.request.Request(url,headers={'User-Agent':'ResearchIdeaPilot/0.1 (academic metadata study)'})
            with urllib.request.urlopen(request,timeout=35) as response:raw=response.read().decode()
            write(base/f'raw_attempt{attempt}.json',raw)
            docs=[]
            for item in json.loads(raw)['message']['items']:
                date=item.get('published',{}).get('date-parts',[[]])[0]
                if date and tuple((date+[1,1])[:3])>(2026,11,2):continue
                docs.append({'doi':item.get('DOI'),'title':' '.join(item.get('title',[])),'date':date,'abstract':html.unescape(re.sub('<[^>]+>',' ',item.get('abstract','')))})
            result={'status':'returned','sources':docs,'scope':'Crossref metadata, not exhaustive novelty evidence','transport_failures':failures}
            write(base/'result.json',result);return result
        except Exception as exc:
            failure={'attempt':attempt,'error':str(exc),'time':now()};failures.append(failure);write(base/f'failure_attempt{attempt}.json',failure)
            if attempt==0:time.sleep(3)
    result={'status':'failed','failures':failures};write(base/'result.json',result);return result

def tools_for(run,case,reply):
    spec=importlib.util.spec_from_file_location('frozen_broker',ROOT/'vendor_broker.py')
    broker=importlib.util.module_from_spec(spec);spec.loader.exec_module(broker)
    cfg={'data_path':str(ROOT/'setup'/f'uci{CASES[case]}.csv'),'data_sha256':sha(ROOT/'setup'/f'uci{CASES[case]}.csv')}
    (run/'tools').mkdir(exist_ok=True)
    seen=set();records=[]
    for i,req in enumerate(reply.get('requests',[])):
        req=dict(req);kind=req.get('type');original_id=req.get('id')
        req['id']=f'{kind}_{i}'
        if kind not in ['compute','search'] or kind in seen:
            result={'status':'blocked','reason':'One compute and one search maximum'}
        else:
            seen.add(kind)
            if kind=='compute':result=broker.compute(run,cfg,req)
            else:result=search(run/'tools'/req['id'],req)
        records.append({'id':original_id,'broker_id':req['id'],'type':kind,'request':req,'result':result})
    write(run/'tool_records.json',records);return records

def sequence(case,arm):
    history=[];library={c['id']:c for c in read(ROOT/'frozen_methods/METHOD_LIBRARY.json')['cards']}
    try:
        for rnd in range(1,4):
            run=ROOT/'runs'/f'{case}_{arm}'/f'r{rnd}';run.mkdir(parents=True,exist_ok=True)
            if (run/'COMPLETE.json').exists():
                history.append(read(run/'round_record.json'));continue
            if any(run.iterdir()):raise RuntimeError('Partial round requires explicit audit; no silent rerun')
            state=[];tools=[];selected=None;cards=[]
            for label in ['L1','R1','L2']:
                bundle={'instruction':(ROOT/'ROLE.md').read_text(),'stage':label,'round':rnd,'strategy_instruction':POLICIES[arm],
                    'original_role_principles':(ROOT/'frozen_methods'/('RESEARCHER_SYSTEM_PROMPT.md' if label=='R1' else 'LEADER_SYSTEM_PROMPT.md')).read_text(),
                    'method_index':(ROOT/'frozen_methods/METHOD_INDEX.md').read_text(),'method_cards':cards,'materials':read(ROOT/'cases'/f'{case}.json'),
                    'history':history,'current_round_replies':state,'actual_tool_returns':tools,'effective_selected_id':selected,
                    'budget':{'role_replies_in_round':3,'compute_calls':1,'search_calls':1,'compute_timeout_seconds':30},
                    'current_data':'DF contains all rows of the fixed CSV with the exact profile column names. TABLES[main]=DF. No hidden outcomes or experiments are supplied.'}
                reply=infer(run/label,bundle);state.append({'stage':label,'reply':reply})
                if label=='L1':
                    selected=effective_selection(reply,arm)
                    write(run/'selection.json',{'proposed':reply['selected_id'],'effective':selected,'rule':POLICIES[arm]})
                    cards=[library[i] for i in reply.get('method_ids',[])[:3] if i in library]
                if label=='R1':tools=tools_for(run,case,reply)
                if label=='L2':assert 'final' in reply
                print(json.dumps({'time':now(),'case':case,'arm':arm,'round':rnd,'stage':label,'status':'complete'}),flush=True)
            record={'round':rnd,'replies':state,'effective_selected_id':selected,'tools':tools}
            write(run/'round_record.json',record)
            write(run/'COMPLETE.json',{'time':now(),'files':{str(p.relative_to(run)):sha(p) for p in sorted(run.rglob('*')) if p.is_file()}})
            history.append(record)
        return {'case':case,'arm':arm,'status':'complete'}
    except Exception as exc:
        path=ROOT/'runs'/f'{case}_{arm}'/'FAILURE.json'
        if not path.exists():write(path,{'time':now(),'error':str(exc),'type':type(exc).__name__})
        return {'case':case,'arm':arm,'status':'failed','error':str(exc)}

def run_all():
    verify_freeze()
    order=[('wine','A'),('shopping','B'),('wine','C'),('shopping','A'),('wine','B'),('shopping','C')]
    with cf.ThreadPoolExecutor(max_workers=3) as pool:
        for result in pool.map(lambda pair:sequence(*pair),order):print(json.dumps(result),flush=True)

def status():
    rows=[]
    for case in CASES:
        for arm in POLICIES:
            seq=ROOT/'runs'/f'{case}_{arm}'
            rows.append({'case':case,'arm':arm,'rounds_completed':len(list(seq.glob('r*/COMPLETE.json'))),'replies_completed':len(list(seq.glob('r*/*/SEALED.json'))),'failure':read(seq/'FAILURE.json') if (seq/'FAILURE.json').exists() else None})
    print(json.dumps(rows,ensure_ascii=False,indent=2))

if __name__=='__main__':
    {'prepare':prepare,'run':run_all,'status':status}[sys.argv[1]]()
