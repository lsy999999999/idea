"""Separately frozen language repair branch; never changes the original F/G round."""
import json
from pathlib import Path
import subprocess
import time
import numpy as np
import experiment as e

ROOT=e.ROOT
BR=ROOT/'revision_R1'
LEAVES=['u','h','history','times','dt','p0','p1','p2','p3','constant']
UNARY=['sum','mean','exp','log','sqrt','abs','sin','cos','tanh']
BINARY=['add','sub','mul','div','pow']

def obj(properties):return dict(type='object',properties=properties,required=list(properties),additionalProperties=False)
def array(items,**kw):return dict(type='array',items=items,**kw)
def string():return dict(type='string')
def schema():
    node=obj(dict(op=dict(type='string',enum=LEAVES+UNARY+BINARY),value=dict(type=['number','null']),args=array({'$ref':'#/$defs/node'},maxItems=2)))
    parameter=obj(dict(name=string(),unit=string(),initial=dict(type='number'),lower=dict(type='number'),upper=dict(type='number')))
    quantity=obj(dict(name=string(),definition=string(),units=string(),availability=string(),initialization_and_future=string()))
    candidate=obj(dict(id=string(),operation=string(),quantities=array(quantity),tree={'$ref':'#/$defs/node'},parameters=array(parameter,minItems=4,maxItems=4),scope=string(),distinguishing_experiment=string()))
    s=obj(dict(candidates=array(candidate,minItems=3,maxItems=3),scientific_notes=string()));s['$defs']={'node':node}
    return s

def expression(n):
    op=n['op'];args=n['args'];v=n['value']
    if op in LEAVES:
        assert not args
        if op=='constant':assert isinstance(v,(int,float));return repr(v)
        if op.startswith('p') and op[1:].isdigit():return 'p['+op[1:]+']'
        return op
    if op in UNARY:assert len(args)==1;return op+'('+expression(args[0])+')'
    assert op in BINARY and len(args)==2
    return '('+expression(args[0])+{'add':'+','sub':'-','mul':'*','div':'/','pow':'**'}[op]+expression(args[1])+')'

def setup():
    BR.mkdir(exist_ok=False)
    s=schema();e.write(BR/'OUTPUT_SCHEMA.json',s)
    # Syntax/semantic fixture; no research input contains this expression.
    pnode=lambda i:dict(op='p'+str(i),value=None,args=[])
    unary=lambda op,n:dict(op=op,value=None,args=[n])
    binary=lambda op,a,b:dict(op=op,value=None,args=[a,b])
    leaf=lambda op:dict(op=op,value=None,args=[])
    fixture=binary('add',binary('mul',pnode(0),leaf('u')),binary('mul',pnode(1),unary('sum',leaf('history'))))
    c=dict(expression=expression(fixture),parameters=[],quantities=[])
    rows=[e.design(.5,.2,[1,2,3,4])]
    assert np.allclose(e.predictor(c)(rows,[2,3,0,0]),[31])
    e.write(BR/'LANGUAGE_CHECK.json',dict(passed=True,scope='AST scalar/vector operations, parameter indexing and raw response mapping; no research efficacy assertion',expression=c['expression']))
    rng=np.random.default_rng(19042)
    hidden=e.observed([e.design(rng.uniform(-1.1,1.1),rng.uniform(0,2.5),rng.uniform(-1,1,4)) for _ in range(128)],19043)
    e.write(BR/'evaluator_only/hidden.json',hidden)
    e.write(BR/'FROZEN.json',dict(time=e.now(),files={str(p.relative_to(ROOT)):e.sha(p) for p in [Path(__file__),ROOT/'REVISION_PROTOCOL.md',BR/'OUTPUT_SCHEMA.json',BR/'LANGUAGE_CHECK.json',BR/'evaluator_only/hidden.json']},visibility='Only serialized bundle; no source, hidden data or evaluator access'))

def infer():
    e.verify_design()
    for p,h in e.read(BR/'FROZEN.json')['files'].items():assert e.sha(ROOT/p)==h
    assert len(list((ROOT/'calls').glob('*/reply.json')))<6
    dest=ROOT/'calls/02b_revision_R1';dest.mkdir(exist_ok=False)
    bundle=dict(stage='new finite revision after original execution failures; not a retry or replacement of original candidates',evidence=e.read(ROOT/'visible/evidence.json'),constraint=e.read(ROOT/'CONSTRAINT_AUDIT.json'),generator_config=e.read(ROOT/'configs/G.json'),prior_candidates={a:e.read(ROOT/f'candidates/{a}_raw.json') for a in ['F','G']},execution_feedback=e.read(ROOT/'DEVELOPMENT_RESULTS.json'),feedback='F C1/C2 exceeded four shared parameters. G C1/C3 referenced undeclared p[4] despite four declarations. R1 must generate a complete replacement with exactly four declared parameter slots and no additional fitted constants. A rewrite need not preserve the old intercept or a separate linear h term; all supplied arguments may enter composable nonlinear interactions. Additional state sensor z is not an available executable interface. Use supplied recorded inputs. Do not presume a unique mechanism.',language=dict(node='Each node has op, value, args. Leaves u,h,history,times,dt,p0,p1,p2,p3 use value=null,args=[]. A constant has numeric value,args=[]. Unary operations have exactly one argument; binary operations have two. Vector arithmetic broadcasts and sum/mean reduce to scalars. Final tree must return scalar raw o.',unary=UNARY,binary=BINARY,parameters='Exactly four declared shared parameters, index 0-3, finite lower < initial < upper. No p4 leaf exists. Parameters may be unused if fewer are needed.',quantities='Annotate any interpretable subexpression in words with definition, units and prospective availability. The complete tree includes its actual calculation; do not refer to undeclared quantity symbols.'),output_schema_reference='CLI structured schema supplied; exactly 3 candidates. Do not use tools.',instruction='Use only this evidence. Generate 3 distinct feasible complete mathematical predictors. Fit-only fitting and dev screening will follow. Choose informative full-model revisions; keep prediction and mechanism separate. Output one JSON object.')
    e.write(dest/'input.json',bundle);prompt='Controlled research model inference. No tools, file access, memory, network or delegation. Use only the following JSON bundle.\n'+json.dumps(bundle,ensure_ascii=False);e.write(dest/'prompt.txt',prompt)
    cmd=[e.CLI,'exec','--ephemeral','--skip-git-repo-check','--model','gpt-6-luna','-c','model_reasoning_effort="low"','--sandbox','read-only','--color','never','--json','--output-schema',str(BR/'OUTPUT_SCHEMA.json'),'--output-last-message',str(dest/'output_0.txt'),'-C',str(ROOT),'-']
    e.write(dest/'command_0.json',cmd);e.event('inference_started',label=dest.name,input_sha256=e.sha(dest/'input.json'))
    start=time.monotonic()
    with (dest/'events_0.jsonl').open('x') as out,(dest/'stderr_0.txt').open('x') as err:
        proc=subprocess.run(cmd,input=prompt,text=True,stdout=out,stderr=err,timeout=600)
    usage={};violations=[]
    for line in (dest/'events_0.jsonl').read_text().splitlines():
        try:ev=json.loads(line)
        except json.JSONDecodeError:continue
        if ev.get('type')=='turn.completed':usage=ev.get('usage',{})
        if ev.get('item',{}).get('type') in ['command_execution','mcp_tool_call','web_search','file_change']:violations.append(ev['item']['type'])
    e.write(dest/'completion_0.json',dict(time=e.now(),returncode=proc.returncode,seconds=time.monotonic()-start,usage=usage,tool_violations=violations,requested_model='gpt-6-luna',requested_reasoning='low',backend_weight_independently_verified=False))
    assert proc.returncode==0 and not violations
    raw=json.loads((dest/'output_0.txt').read_text());e.write(dest/'reply.json',raw);e.write(dest/'SEALED.json',dict(time=e.now(),input_sha256=e.sha(dest/'input.json'),reply_sha256=e.sha(dest/'reply.json')))
    e.write(BR/'raw_candidates.json',raw)
    converted=[]
    for c in raw['candidates']:
        assert len(c['parameters'])==4
        converted.append(dict(c,expression=expression(c['tree']),quantities=[],quantity_annotations=c['quantities']))
    e.write(BR/'converted_candidates.json',converted)
    e.event('raw_candidates_saved',arm='revision_R1',count=len(raw['candidates']),sha256=e.sha(BR/'raw_candidates.json'))
    print(json.dumps(dict(expressions=[c['expression'] for c in converted]),ensure_ascii=False))

def evaluate():
    ev=e.read(ROOT/'visible/evidence.json');items=e.read(BR/'converted_candidates.json');results=[e.fit_candidate(c,ev) for c in items]
    e.write(BR/'DEVELOPMENT_RESULTS.json',results)
    viable=[i for i,r in enumerate(results) if r.get('dev_accepted')];selected=min(viable,key=lambda i:results[i]['dev_rmse']) if viable else None
    e.write(BR/'SELECTION_FREEZE.json',dict(time=e.now(),selected=selected,raw_candidates_sha256=e.sha(BR/'raw_candidates.json'),development_sha256=e.sha(BR/'DEVELOPMENT_RESULTS.json'),hidden_loaded=False))
    # E9/E10 were not included in first round's cap of eight designs.
    previous={r['id'] for r in e.read(ROOT/'PREDICTION_FREEZE.json')['designs']}
    designs=[r for r in ev['experiment_catalog'] if r['id'] in ['E9','E10']];assert not previous.intersection(r['id'] for r in designs)
    forecast=[]
    for c,r in zip(items,results):forecast.append(dict(id=c['id'],predictions=e.predictor(c)(designs,r['parameters']).tolist() if r.get('prediction_valid') else None))
    e.write(BR/'PREDICTION_FREEZE.json',dict(time=e.now(),designs=designs,predictions=forecast,selection_sha256=e.sha(BR/'SELECTION_FREEZE.json')))
    e.event('revision_prediction_frozen',sha256=e.sha(BR/'PREDICTION_FREEZE.json'))
    new=e.observed([dict(r,repeat=k) for r in designs for k in range(4)],19044)
    e.write(BR/'NEW_EXPERIMENT.json',dict(time=e.now(),rows=new,prediction_freeze_sha256=e.sha(BR/'PREDICTION_FREEZE.json'),scope='Fresh E9/E10; same raw target, calibrated reference and bounded noise; no refit'))
    hidden=e.read(BR/'evaluator_only/hidden.json');ind=[]
    for c,r in zip(items,results):
        row=dict(id=c['id'],selected=selected==len(ind),independently_valid=False)
        if r.get('prediction_valid'):
            predict=e.predictor(c);p=r['parameters'];row['hidden_rmse']=float(np.sqrt(np.mean((predict(hidden,p)-[x['o'] for x in hidden])**2)));row['new_experiment_rmse']=float(np.sqrt(np.mean((predict(new,p)-[x['o'] for x in new])**2)));row['independently_valid']=bool(r['dev_accepted'] and row['hidden_rmse']<=.06)
        ind.append(row)
    e.write(BR/'INDEPENDENT_RESULTS.json',dict(time=e.now(),results=ind,selection_sha256=e.sha(BR/'SELECTION_FREEZE.json'),prediction_sha256=e.sha(BR/'PREDICTION_FREEZE.json'),hidden_sha256=e.sha(BR/'evaluator_only/hidden.json')))
    e.event('revision_new_evidence_obtained',sha256=e.sha(BR/'NEW_EXPERIMENT.json'))
    print(json.dumps(dict(development=results,selected=selected,independent=ind),ensure_ascii=False))

if __name__=='__main__':
    import sys
    if sys.argv[1]=='setup':setup()
    elif sys.argv[1]=='infer':infer()
    elif sys.argv[1]=='evaluate':evaluate()
