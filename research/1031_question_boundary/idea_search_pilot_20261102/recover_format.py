"""Prospectively documented formatting-only continuation; original runs untouched."""
import concurrent.futures as cf
import json
from pathlib import Path
import shutil
import sys
sys.dont_write_bytecode=True
import pilot as p

BASE=p.ROOT
REC=BASE/'format_recovery'
original_infer=p.infer

def safe_parse(raw):
    raw=raw.strip()
    if raw.startswith('```'):
        import re
        raw=re.sub(r'^```(?:json)?\s*','',raw);raw=re.sub(r'\s*```$','',raw)
    try:return json.loads(raw),False
    except json.JSONDecodeError:
        obj,end=json.JSONDecoder().raw_decode(raw)
        assert isinstance(obj,dict) and raw[end:].strip()=='}', 'Not the declared single-extra-brace error'
        return obj,True

def inferred(path,bundle):
    if (path/'reply.json').exists():
        assert p.read(path/'input.json')==bundle,'Existing input differs'
        return p.read(path/'reply.json')
    if not (path/'input.json').exists():
        try:return original_infer(path,bundle)
        except json.JSONDecodeError:pass
    assert p.read(path/'input.json')==bundle,'Partial input differs'
    completions=sorted(path.glob('completion_attempt*.json'))
    assert completions
    completion=p.read(completions[-1]);assert completion['returncode']==0 and not completion['tool_violations']
    attempt=completions[-1].stem.split('attempt')[-1]
    rawpath=path/f'reply_attempt{attempt}.txt'
    reply,changed=safe_parse(rawpath.read_text())
    assert changed, 'Expected only the documented JSON error'
    p.write(path/'FORMAT_RECOVERY.json',{'time':p.now(),'rule':'Unique complete leading JSON dictionary plus exactly one surplus closing brace','raw_sha256':p.sha(rawpath),'scientific_content_changed':False,'model_regenerated':False})
    p.write(path/'reply.json',reply)
    p.write(path/'SEALED.json',{'time':p.now(),'input_sha256':p.sha(path/'input.json'),'reply_sha256':p.sha(path/'reply.json'),'format_recovery':True})
    return reply

def prepare():
    assert not REC.exists()
    # Caller verifies the original worker has exited before this snapshot.
    REC.mkdir()
    for name in ['setup','cases','frozen_methods','runs']:
        shutil.copytree(BASE/name,REC/name)
    for name in ['pilot.py','vendor_broker.py','ROLE.md','PROTOCOL.md','POLICIES.json','FROZEN_DESIGN.json','REVIEW_INSTRUCTIONS.md','review.py','REVIEW_PREFREEZE.json','mask_review_paths.py','audit.py']:
        shutil.copy2(BASE/name,REC/name)
    for failure in (REC/'runs').glob('*/FAILURE.json'):failure.rename(failure.with_name('STRICT_PROTOCOL_FAILURE.json'))
    p.write(REC/'RECOVERY_DESIGN.json',{'time':p.now(),'base':str(BASE),'protocol_sha256':p.sha(BASE/'FORMAT_RECOVERY_PROTOCOL.md'),'runner_sha256':p.sha(Path(__file__)),'original_completed_rounds':len(list((BASE/'runs').glob('*/r*/COMPLETE.json'))),'original_completed_replies':len(list((BASE/'runs').glob('*/r*/*/SEALED.json'))),'original_freeze_sha256':p.sha(BASE/'FROZEN_DESIGN.json')})
    print('Recovery snapshot prepared',flush=True)

def sequence(case,arm):
    history=[];library={c['id']:c for c in p.read(REC/'frozen_methods/METHOD_LIBRARY.json')['cards']}
    try:
        for rnd in range(1,4):
            run=REC/'runs'/f'{case}_{arm}'/f'r{rnd}';run.mkdir(parents=True,exist_ok=True)
            if (run/'COMPLETE.json').exists():history.append(p.read(run/'round_record.json'));continue
            state=[];tools=[];selected=None;cards=[]
            for label in ['L1','R1','L2']:
                bundle={'instruction':(REC/'ROLE.md').read_text(),'stage':label,'round':rnd,'strategy_instruction':p.POLICIES[arm],
                    'original_role_principles':(REC/'frozen_methods'/('RESEARCHER_SYSTEM_PROMPT.md' if label=='R1' else 'LEADER_SYSTEM_PROMPT.md')).read_text(),
                    'method_index':(REC/'frozen_methods/METHOD_INDEX.md').read_text(),'method_cards':cards,'materials':p.read(REC/'cases'/f'{case}.json'),
                    'history':history,'current_round_replies':state,'actual_tool_returns':tools,'effective_selected_id':selected,
                    'budget':{'role_replies_in_round':3,'compute_calls':1,'search_calls':1,'compute_timeout_seconds':30},
                    'current_data':'DF contains all rows of the fixed CSV with the exact profile column names. TABLES[main]=DF. No hidden outcomes or experiments are supplied.'}
                reply=inferred(run/label,bundle);state.append({'stage':label,'reply':reply})
                if label=='L1':
                    selected=p.effective_selection(reply,arm)
                    p.same_or_write(run/'selection.json',{'proposed':reply['selected_id'],'effective':selected,'rule':p.POLICIES[arm]})
                    cards=[library[i] for i in reply.get('method_ids',[])[:3] if i in library]
                if label=='R1':tools=p.read(run/'tool_records.json') if (run/'tool_records.json').exists() else p.tools_for(run,case,reply)
                if label=='L2':assert 'final' in reply
                print(json.dumps({'time':p.now(),'case':case,'arm':arm,'round':rnd,'stage':label,'status':'complete_or_reused'}),flush=True)
            record={'round':rnd,'replies':state,'effective_selected_id':selected,'tools':tools}
            p.write(run/'round_record.json',record)
            p.write(run/'COMPLETE.json',{'time':p.now(),'files':{str(f.relative_to(run)):p.sha(f) for f in sorted(run.rglob('*')) if f.is_file()},'format_recovery_branch':True})
            history.append(record)
        return {'case':case,'arm':arm,'status':'complete'}
    except Exception as exc:
        f=REC/'runs'/f'{case}_{arm}'/'RECOVERY_FAILURE.json'
        if not f.exists():p.write(f,{'time':p.now(),'error':str(exc),'type':type(exc).__name__})
        return {'case':case,'arm':arm,'status':'failed','error':str(exc)}

def run():
    p.ROOT=REC;p.verify_freeze()
    order=[('wine','A'),('shopping','B'),('wine','C'),('shopping','A'),('wine','B'),('shopping','C')]
    with cf.ThreadPoolExecutor(max_workers=3) as pool:
        for result in pool.map(lambda pair:sequence(*pair),order):print(json.dumps(result),flush=True)

if __name__=='__main__':{'prepare':prepare,'run':run}[sys.argv[1]]()
