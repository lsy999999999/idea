"""Bounded brokered tool-use development pilot. Raw observations only to Luna."""
import copy
import datetime
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import time
import numpy as np
from model_language import Model, fit, rmse, RAW
from tools import infer_units, representation_check, complete_model, automatic_library

ROOT=Path(__file__).resolve().parent
PREVIOUS=ROOT.parent/'structure_composition_pilot_20261103'
RECOVERY=ROOT.parent/'structure_search_recovery_20261103'
STERILE=Path('/private/tmp/idea-tool-pilot-20261103-inference')
CLI='/opt/homebrew/bin/codex'
spec=importlib.util.spec_from_file_location('organizer_evaluator',RECOVERY/'evaluator.py')
evaluator=importlib.util.module_from_spec(spec);spec.loader.exec_module(evaluator)

def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x') as f:f.write(v if isinstance(v,str) else json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False))
def cached(p,fn):
    if Path(p).exists():return read(p)
    value=fn();write(p,value);return value
def obj(p):return dict(type='object',properties=p,required=list(p),additionalProperties=False)
def arr(x,**kw):return dict(type='array',items=x,**kw)
S=dict(type='string');N=dict(type='number')
PARAM=obj(dict(name=S,lower=N,initial=N,upper=N))
QUANTITY=obj(dict(name=S,expression=S,interpretation=S))
DESIGN=obj(dict(u=N,h=N,history=arr(N,minItems=4,maxItems=4),purpose=S))
ANNOTATION=dict(scientific_change=S,evidence_refs=arr(S),prospective_contrast=S,refutation_condition=S,experiments=arr(DESIGN,maxItems=4))
SCHEMAS=dict(direct=obj(dict(parameters=arr(PARAM,maxItems=8),quantities=arr(QUANTITY,maxItems=4),expression=S,**ANNOTATION)),
 agent_tools=obj(dict(action=dict(type='string',enum=['representation_check','complete_model']),parameters=arr(PARAM,maxItems=2),quantities=arr(QUANTITY,maxItems=4),features=arr(S,minItems=1,maxItems=4),degree=dict(type='integer',enum=[1,2,3]),**ANNOTATION)))
LANGUAGE=dict(raw_inputs=dict(u='dimensionless scalar current drive',h='waiting time in seconds',history='4 dimensionless previous drives, oldest first',times='4 interval end times relative to drive, seconds',dt='history interval duration, seconds'),
 operators=['+','-','*','/','**','sum','mean','exp','log','sqrt','abs','sin','cos','tanh','constant vector indexing [0]..[3]'],
 fixed_context=dict(times=[-4.,-3.,-2.,-1.],dt=1.),
 syntax='Named shared parameters, finite lower < initial < upper. Quantities defined sequentially from raw inputs, parameters and earlier quantities. Vector arithmetic broadcasts scalar. sum/mean reduce. No row ids, observed responses, per-row constants, arbitrary code or indexing of parameters. Output is raw response. Tool infers parameter units; exp/log/trigonometric arguments must be dimensionless. No need to introduce a new quantity if unsupported.',
 experiments='Up to four NEW conditions: u [-1.1,1.1], h [0,2.5], history length4 each [-1,1]. Only these inputs and scalar response are measurable; no internal-state sensor. Future confirmation after all revision ends.')

def verify():
    frozen=read(ROOT/'FROZEN.json')
    for p,h in frozen['files'].items():assert sha(ROOT/p)==h,p
    for p,h in frozen['previous_files'].items():assert sha(PREVIOUS/p)==h,p
    assert sha(STERILE/'AGENTS.md')==frozen['sterile_sha256']

def prepare():
    from checks import run
    for p,h in read(PREVIOUS/'RESULTS_SEAL.json')['files'].items():assert sha(PREVIOUS/p)==h,p
    write(ROOT/'IMPLEMENTATION_CHECKS.json',run())
    old=read(PREVIOUS/'visible/evidence.json')
    ev={k:old[k] for k in ['metadata','fit','dev']}
    write(ROOT/'visible/evidence.json',ev)
    rng=np.random.default_rng(31103401)
    def design():return dict(u=float(rng.uniform(-1.1,1.1)),h=float(rng.uniform(0,2.5)),history=rng.uniform(-1,1,4).tolist(),times=[-4.,-3.,-2.,-1.],dt=1.)
    write(ROOT/'evaluator_only/hidden.json',evaluator.acquire([design() for _ in range(200)],31103402,1))
    write(ROOT/'confirmation_designs.json',[dict(design(),source='random_confirmation',design_id='random_'+str(i)) for i in range(16)])
    for k,v in SCHEMAS.items():write(ROOT/(k+'_schema.json'),v)
    full=automatic_library()
    catalogs=[full,dict(full,features=[f for f in full['features'] if 'sin(' not in f and 'cos(' not in f]),
      dict(full,features=[f for f in full['features'] if 'tanh(' not in f]),
      dict(full,parameters=[],features=[f for f in full['features'] if 'scale' not in f])]
    write(ROOT/'tool_only_catalogs.json',catalogs)
    STERILE.mkdir(exist_ok=False)
    write(STERILE/'AGENTS.md','Inference-only directory. Use only supplied serialized task. Do not use native tools, files, memory, network, shell, or delegation. For agent_tools choose a brokered tool in your JSON reply; the experiment runner executes it and returns results next turn.\n')
    files=['run.py','tools.py','model_language.py','checks.py','PROTOCOL.md','IMPLEMENTATION_CHECKS.json','visible/evidence.json','evaluator_only/hidden.json','confirmation_designs.json','direct_schema.json','agent_tools_schema.json','tool_only_catalogs.json','../structure_search_recovery_20261103/evaluator.py']
    write(ROOT/'FROZEN.json',dict(time=now(),files={p:sha(ROOT/p) for p in files},previous_files=read(PREVIOUS/'RESULTS_SEAL.json')['files'],sterile_sha256=sha(STERILE/'AGENTS.md'),model='gpt-6-luna',effort='low',call_cap=8,decision_calls_per_llm_arm=4,fit_rows=len(ev['fit']),dev_rows=len(ev['dev']),scope='Repeated development mechanism; no open discovery or novelty claim'))
    print(json.dumps(dict(prepared=True,checks=len(read(ROOT/'IMPLEMENTATION_CHECKS.json')),fit=len(ev['fit']),dev=len(ev['dev']))),flush=True)

def infer(index,arm,bundle):
    verify();assert 1<=index<=8
    dest=ROOT/'calls'/f'{index:02d}_{arm}'
    prompt='Controlled scientific modeling. Use only the JSON evidence and prior within-condition tool outputs. Return one JSON object. Do not use native tools, files, memory, network, shell or delegation.\n'+json.dumps(bundle,ensure_ascii=False)
    if dest.exists():
        assert read(dest/'input.json')==bundle
        if (dest/'reply.json').exists():return read(dest/'reply.json')
    else:dest.mkdir(parents=True);write(dest/'input.json',bundle);write(dest/'prompt.txt',prompt)
    for attempt in range(2):
        done=dest/f'completion_{attempt}.json'
        if done.exists():
            if read(done)['returncode']==0:raise RuntimeError('Successful raw output requires audit; no new scientific retry')
            continue
        cmd=[CLI,'exec','--ephemeral','--skip-git-repo-check','--model','gpt-6-luna','-c','model_reasoning_effort="low"','--sandbox','read-only','--color','never','--json','--output-schema',str(ROOT/(arm+'_schema.json')),'--output-last-message',str(dest/f'output_{attempt}.txt'),'-C',str(STERILE),'-']
        write(dest/f'command_{attempt}.json',cmd);start=time.monotonic()
        with (dest/f'events_{attempt}.jsonl').open('x') as out,(dest/f'stderr_{attempt}.txt').open('x') as err:
            try:rc=subprocess.run(cmd,input=prompt,text=True,stdout=out,stderr=err,timeout=600).returncode
            except subprocess.TimeoutExpired:rc=124
        usage={};violations=[]
        for line in (dest/f'events_{attempt}.jsonl').read_text().splitlines():
            try:event=json.loads(line)
            except json.JSONDecodeError:continue
            if event.get('type')=='turn.completed':usage=event.get('usage',{})
            if event.get('item',{}).get('type') in ['command_execution','mcp_tool_call','web_search','file_change']:violations.append(event['item']['type'])
        write(done,dict(time=now(),returncode=rc,seconds=time.monotonic()-start,usage=usage,tool_violations=violations,requested_model='gpt-6-luna',requested_reasoning='low',backend_weights_verified=False))
        if rc:raise RuntimeError('Transport failed; preserve logs and resume identical input only')
        if violations:raise RuntimeError('Prohibited native tool use')
        raw=(dest/f'output_{attempt}.txt').read_text().strip();raw=re.sub(r'^```(?:json)?\s*|\s*```$','',raw)
        reply=json.loads(raw);write(dest/'reply.json',reply);write(dest/'SEALED.json',dict(time=now(),input_sha256=sha(dest/'input.json'),reply_sha256=sha(dest/'reply.json')))
        print(json.dumps(dict(call=index,arm=arm,usage=usage)),flush=True);return reply
    raise RuntimeError('Transport retries exhausted')

def request_of(reply):return {k:reply[k] for k in ['parameters','quantities','features','degree']}
def compact(result):
    result=copy.deepcopy(result)
    result.pop('dev_predictions',None)
    if 'best' in result:result['best'].pop('manifest',None)
    return result

def direct_execute(reply,ev):
    try:
        parameters,audit=infer_units(reply['parameters'],reply['quantities'],[],expression=reply['expression'])
        scaffold=dict(parameters=parameters,quantities=reply['quantities'],exposed_inputs=list(RAW))
        result=fit(scaffold,reply['expression'],ev['fit'],ev['dev'])
        c=[]
        if result['status']=='executed' and result['optimizer_converged']:
            c=[dict(scaffold=scaffold,expression=reply['expression'],values=result['values'],train_rmse=result['fit_rmse'],dev_rmse=result['dev_rmse'],optimizer_converged=True,annotation=reply)]
        return dict(result=result,unit_audit=audit,candidates=c)
    except Exception as exc:return dict(result=dict(status='invalid_request',error=str(exc)),candidates=[])

def tool_execute(reply,ev,log,budget):
    try:
        request=request_of(reply)
        if reply['action']=='representation_check':return dict(result=representation_check(request,ev['dev'],ev['metadata']),candidates=[])
        result,candidates=complete_model(request,ev['fit'],ev['dev'],ev['metadata'],log,budget)
        for c in candidates:c['annotation']=reply
        return dict(result=result,candidates=candidates)
    except Exception as exc:return dict(result=dict(status='invalid_request',error=str(exc)),candidates=[])

def llm_arm(arm,ev,offset):
    history=[];pool=[];budget=dict(residual_calls=0,linear_solves=0)
    for step in range(1,5):
        bundle=dict(condition=arm,decision=step,decisions_total=4,evidence=ev,language=LANGUAGE,previous_steps=history,
          goal='Revise the insufficient o=f(u,h) into a testable response using evidence. Independently choose meaningful quantities or function structure; do not add a latent variable merely by name. Explain which retained assumption changes and prospective contrast that could refute it.',
          acceptance='Shared fitted parameters. All fit on fit only. Select model on dev. Raw-response RMSE <=0.06 on dev plus later independent data. You will not receive independent targets for revision.',
          resource_limits=dict(parameters_total=8,residual_calls_per_fit=1600,residual_calls_condition=6400),)
        if arm=='direct':bundle['instruction']='Submit one complete response equation with all named parameters and sequential quantities. Tool infers units, compiles and fits only the formula you specify. Next decision receives numerical feedback; full scientific rewriting is allowed.'
        else:
            bundle['instruction']='Choose one actual brokered tool action. representation_check tests exact feature collisions before completing a formula. complete_model fits a sparse polynomial response over ONLY the scalar features you specify, including interactions up to degree. You choose the feature representation and nonlinear functional structure. Tool supplies independent coefficients of response units, at most 8 total parameters, of which at most 2 are your nonlinear parameters. Use features to expose all information the downstream response may use. Define up to4 named quantities and 1..4 scalar features. Degree 1..3. Revisions and whole-model replacement are allowed. A check consumes one decision and returns no predictive model. Your last decision should complete a model if possible.'
            bundle['completion_details']='Forward term selection and nonlinear variable projection use fit only. Among fit-converged models dev selects the best. Extra basis terms may include powers/products of features you choose. This tool cannot invent a missing feature or a transformation of history unless you specify it.'
        reply=infer(offset+step,arm,bundle)
        def execute():
            if arm=='direct':return direct_execute(reply,ev)
            return tool_execute(reply,ev,ROOT/'search_traces'/f'{arm}_{step}.jsonl',budget)
        path=ROOT/'steps'/f'{arm}_{step}.json'
        if path.exists():
            saved=read(path);result=saved['execution'];budget=saved['budget_after']
        else:
            start=time.monotonic();result=execute()
            if arm=='direct':budget['residual_calls']+=result['result'].get('residual_calls',0)
            write(path,dict(time=now(),seconds=time.monotonic()-start,execution=result,budget_after=budget.copy()))
        for i,c in enumerate(result['candidates']):
            c=dict(c,id=f'{arm}_{step}_{i}',step=step);pool.append(c)
        history.append(dict(step=step,proposal=reply,tool_feedback=compact(result['result'])))
        print(json.dumps(dict(arm=arm,step=step,status=result['result'].get('status','checked'),dev_rmse=result['result'].get('dev_rmse',result['result'].get('best',{}).get('dev_rmse')),budget=budget)),flush=True)
    write_if_absent=ROOT/'arms'/(arm+'.json')
    return cached(write_if_absent,lambda:dict(history=history,pool=pool,budget=budget))

def tool_only(ev):
    pool=[];history=[];budget=dict(residual_calls=0,linear_solves=0)
    for step,request in enumerate(read(ROOT/'tool_only_catalogs.json'),1):
        path=ROOT/'steps'/f'tool_only_{step}.json'
        if path.exists():saved=read(path);execution=saved['execution'];budget=saved['budget_after']
        else:
            start=time.monotonic()
            reply=dict(request,action='complete_model')
            execution=tool_execute(reply,ev,ROOT/'search_traces'/f'tool_only_{step}.jsonl',budget)
            write(path,dict(time=now(),seconds=time.monotonic()-start,execution=execution,budget_after=budget.copy()))
        for i,c in enumerate(execution['candidates']):pool.append(dict(c,id=f'tool_only_{step}_{i}',step=step))
        history.append(dict(request=request,result=compact(execution['result'])))
        print(json.dumps(dict(arm='tool_only',step=step,status=execution['result'].get('status'),best=execution['result'].get('best',{}).get('dev_rmse'),budget=budget)),flush=True)
    return cached(ROOT/'arms/tool_only.json',lambda:dict(history=history,pool=pool,budget=budget))

def design_key(r):return tuple([r['u'],r['h'],*r['history'],*r['times'],r['dt']])

def independent(arms,ev):
    selected={}
    for arm,data in arms.items():
        pool=sorted(data['pool'],key=lambda c:(c['dev_rmse'],len(c['values']),c['id']))
        selected[arm]=pool[0] if pool else None
    cached(ROOT/'SELECTION_FREEZE.json',lambda:dict(time=now(),selected=selected,hidden_read=False,confirmation_acquired=False))
    designs=read(ROOT/'confirmation_designs.json');seen={design_key(r) for r in ev['fit']+ev['dev']+designs};rejected=[]
    for arm in ['direct','agent_tools']:
        c=selected[arm]
        if not c:continue
        for i,r in enumerate(c['annotation']['experiments']):
            try:
                assert len(r['history'])==4 and all(math.isfinite(x) for x in [r['u'],r['h'],*r['history']])
                assert -1.1<=r['u']<=1.1 and 0<=r['h']<=2.5 and all(-1<=x<=1 for x in r['history'])
                d=dict(u=r['u'],h=r['h'],history=r['history'],times=[-4.,-3.,-2.,-1.],dt=1.,source='proposed_confirmation',design_id=f'{arm}_{i}')
                assert design_key(d) not in seen,'Previously observed or duplicate design'
                designs.append(d);seen.add(design_key(d))
            except Exception as exc:rejected.append(dict(arm=arm,request=r,error=str(exc) or 'Invalid interface bounds'))
    forecast={}
    for arm,c in selected.items():
        forecast[arm]=None if c is None else Model(c['scaffold'],c['expression']).predict(designs,c['values']).tolist()
    cached(ROOT/'PREDICTION_FREEZE.json',lambda:dict(time=now(),designs=designs,predictions=forecast,rejected=rejected,selection_sha256=sha(ROOT/'SELECTION_FREEZE.json')))
    fresh=cached(ROOT/'NEW_OBSERVATIONS.json',lambda:dict(time=now(),rows=evaluator.acquire(designs,31103403,4),prediction_sha256=sha(ROOT/'PREDICTION_FREEZE.json')))['rows']
    hidden=read(ROOT/'evaluator_only/hidden.json');results=[]
    for arm,c in selected.items():
        result=dict(arm=arm,accepted=False)
        if c is not None:
            m=Model(c['scaffold'],c['expression']);v=c['values']
            result.update(candidate_id=c['id'],dev_rmse=c['dev_rmse'],hidden_rmse=rmse(m.predict(hidden,v),hidden))
            for source in ['random_confirmation','proposed_confirmation']:
                rows=[r for r in fresh if r['source']==source]
                result[source+'_rmse']=rmse(m.predict(rows,v),rows) if rows else None
            result['accepted']=all(value<=.06 for key,value in result.items() if key.endswith('rmse') and value is not None)
            replay=rmse(m.predict(ev['dev'],v),ev['dev'])
            assert abs(replay-c['dev_rmse'])<1e-10,'Selected point differs from recorded dev metric'
            result['selected_parameters']=dict(zip([p['name'] for p in c['scaffold']['parameters']],v))
        results.append(result)
    return cached(ROOT/'INDEPENDENT_RESULTS.json',lambda:dict(time=now(),results=results,hidden_rows=len(hidden),confirmation_rows=len(fresh),confirmation_conditions=len(designs)))

def run():
    verify();ev=read(ROOT/'visible/evidence.json')
    arms={};arms['direct']=llm_arm('direct',ev,0);arms['tool_only']=tool_only(ev);arms['agent_tools']=llm_arm('agent_tools',ev,4)
    result=independent(arms,ev);verify();usage={}
    for p in (ROOT/'calls').glob('*/completion_*.json'):
        item=read(p)
        for k,v in item['usage'].items():usage[k]=usage.get(k,0)+v
    summary=dict(time=now(),research_calls=len(list((ROOT/'calls').glob('*/reply.json'))),arms={k:dict(complete_candidates=len(v['pool']),budget=v['budget']) for k,v in arms.items()},independent=result,usage=usage,scope='One development chain per condition, repeated known mechanism. No average method benefit, mechanism uniqueness, or scientific novelty established.')
    cached(ROOT/'SUMMARY.json',lambda:summary);print(json.dumps(summary,ensure_ascii=False),flush=True)

if __name__=='__main__':
    if sys.argv[1]=='prepare':prepare()
    elif sys.argv[1]=='run':run()
