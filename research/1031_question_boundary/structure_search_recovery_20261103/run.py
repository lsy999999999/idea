"""Frozen bounded recovery experiment. Inference gets JSON only, no simulator."""
import datetime
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import time
import numpy as np
import evaluator
from model_language import Model, capacity_audit, fit, rmse

ROOT=Path(__file__).resolve().parent
OLD=ROOT.parent/'structure_search_stage1_20261103'
STERILE=Path('/private/tmp/idea-recovery-20261103-inference')
CLI='/opt/homebrew/bin/codex'


def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def read(p): return json.loads(Path(p).read_text())
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,obj):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x') as f: f.write(obj if isinstance(obj,str) else json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False))
def cached(p,fn):
    if Path(p).exists(): return read(p)
    value=fn();write(p,value);return value
def object_schema(props): return dict(type='object',properties=props,required=list(props),additionalProperties=False)
def array(items,**kw): return dict(type='array',items=items,**kw)
S=dict(type='string');N=dict(type='number')


def schemas():
    parameter=object_schema(dict(name=S,dimension=array(dict(type='integer'),minItems=2,maxItems=2),lower=N,initial=N,upper=N))
    quantity=object_schema(dict(name=S,expression=S,interpretation=S))
    design=object_schema(dict(u=N,h=N,history=array(N,minItems=4,maxItems=4),purpose=S))
    build=object_schema(dict(parameters=array(parameter,maxItems=8),quantities=array(quantity,maxItems=8),
                            exposed_inputs=array(dict(type='string',enum=['u','h','history','times','dt']),maxItems=5),
                            rationale=S,evidence_refs=array(S),experiments=array(design,maxItems=4),measurement_requests=array(S)))
    finish=object_schema(dict(expression=S,scientific_change=S,predicted_contrasts=array(S)))
    return dict(build=build,finish=finish)


def prepare():
    from checks import run
    checks=run();write(ROOT/'IMPLEMENTATION_CHECKS.json',checks)
    old=read(OLD/'visible/evidence.json')
    def rows_with_ids(rows,prefix):
        return [dict({k:r[k] for k in ['u','h','history','times','dt','o']},row_id=prefix+str(i)) for i,r in enumerate(rows)]
    train=rows_with_ids(old['fit'],'fit_');dev=rows_with_ids(old['dev'],'dev_')
    dev+=rows_with_ids(read(OLD/'NEW_EXPERIMENT.json')['rows'],'observed_A_')
    dev+=rows_with_ids(read(OLD/'revision_R1/NEW_EXPERIMENT.json')['rows'],'observed_B_')
    visible=dict(metadata=old['metadata'],fit=train,dev=dev)
    write(ROOT/'visible/evidence.json',visible)
    write(ROOT/'evaluator_only/hidden.json',evaluator.hidden())
    for name,sc in schemas().items():write(ROOT/(name+'_schema.json'),sc)
    STERILE.mkdir(exist_ok=False)
    write(STERILE/'AGENTS.md','This directory is an inference-only context. Answer the supplied JSON task directly. Do not use tools, read files or memory, access network, or delegate.\n')
    source_files=['run.py','model_language.py','checks.py','evaluator.py','PROTOCOL.md','build_schema.json','finish_schema.json','visible/evidence.json','evaluator_only/hidden.json','IMPLEMENTATION_CHECKS.json']
    prior={str(p.relative_to(OLD)):sha(p) for p in OLD.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    write(ROOT/'FROZEN.json',dict(time=now(),files={p:sha(ROOT/p) for p in source_files},prior_stage_files=prior,
          sterile_instructions_sha256=sha(STERILE/'AGENTS.md'),research_model='gpt-6-luna',effort='low',call_cap=6,
          scope='Same development mechanism; raw observations only, no previous candidate formulas or organizer structure diagnoses'))
    print(json.dumps(dict(prepared=True,checks=len(checks),fit_rows=len(train),dev_rows=len(dev),source_files=len(source_files))))


def verify():
    frozen=read(ROOT/'FROZEN.json')
    for p,h in frozen['files'].items(): assert sha(ROOT/p)==h,p
    for p,h in frozen['prior_stage_files'].items(): assert sha(OLD/p)==h,p
    assert sha(STERILE/'AGENTS.md')==frozen['sterile_instructions_sha256']


def infer(index,stage,bundle):
    verify();assert 1<=index<=6
    dest=ROOT/'calls'/f'{index:02d}_{stage}'
    prompt='Controlled scientific inference. Use only this JSON bundle. Do not use tools, files, memory, network or delegation. Return one JSON object matching the schema.\n'+json.dumps(bundle,ensure_ascii=False)
    if dest.exists():
        assert read(dest/'input.json')==bundle
        if (dest/'reply.json').exists():return read(dest/'reply.json')
    else:
        dest.mkdir(parents=True);write(dest/'input.json',bundle);write(dest/'prompt.txt',prompt)
    completed=list((ROOT/'calls').glob('*/completion_*.json'))
    failed=sum(read(p)['returncode']!=0 for p in completed)
    for attempt in range(2):
        if (dest/f'completion_{attempt}.json').exists():
            if read(dest/f'completion_{attempt}.json')['returncode']==0:raise RuntimeError('Existing successful output needs audit; no scientific retry')
            continue
        if attempt and failed>1:raise RuntimeError('Transport retry cap reached')
        cmd=[CLI,'exec','--ephemeral','--skip-git-repo-check','--model','gpt-6-luna','-c','model_reasoning_effort="low"',
             '--sandbox','read-only','--color','never','--json','--output-schema',str(ROOT/(stage+'_schema.json')),
             '--output-last-message',str(dest/f'output_{attempt}.txt'),'-C',str(STERILE),'-']
        write(dest/f'command_{attempt}.json',cmd)
        start=time.monotonic()
        with (dest/f'events_{attempt}.jsonl').open('x') as out,(dest/f'stderr_{attempt}.txt').open('x') as err:
            try: rc=subprocess.run(cmd,input=prompt,text=True,stdout=out,stderr=err,timeout=600).returncode
            except subprocess.TimeoutExpired:rc=124
        usage={};violations=[]
        for line in (dest/f'events_{attempt}.jsonl').read_text().splitlines():
            try: event=json.loads(line)
            except json.JSONDecodeError:continue
            if event.get('type')=='turn.completed':usage=event.get('usage',{})
            if event.get('item',{}).get('type') in ['command_execution','mcp_tool_call','web_search','file_change']:
                violations.append(event['item']['type'])
        write(dest/f'completion_{attempt}.json',dict(time=now(),returncode=rc,seconds=time.monotonic()-start,usage=usage,
                 tool_violations=violations,requested_model='gpt-6-luna',requested_reasoning='low',backend_weights_verified=False))
        if rc:raise RuntimeError(f'Inference transport failure {rc}; retain output and resume identical input only')
        if violations:raise RuntimeError('Model used a prohibited tool; stop experiment')
        raw=(dest/f'output_{attempt}.txt').read_text().strip();raw=re.sub(r'^```(?:json)?\s*|\s*```$','',raw)
        reply=json.loads(raw);write(dest/'reply.json',reply)
        write(dest/'SEALED.json',dict(time=now(),input_sha256=sha(dest/'input.json'),reply_sha256=sha(dest/'reply.json')))
        print(json.dumps(dict(call=index,stage=stage,completed=True,usage=usage)),flush=True)
        return reply
    raise RuntimeError('Transport attempts exhausted')


LANGUAGE=dict(raw_inputs=dict(u='dimensionless scalar',h='waiting time in seconds',history='four dimensionless prior drive values, oldest first',
             times='four interval end times relative to current drive, in seconds',dt='duration of each history interval, in seconds'),
    operators=['+','-','*','/','**','sum','mean','exp','log','sqrt','abs','sin','cos','tanh','fixed vector indexing [0]..[3]'],
    types='Vector arithmetic broadcasts scalars. sum/mean reduce. Parameters use names, never p[i]. Dimension is [time exponent,response exponent]. Output must have dimension [0,1].',
    construction='Define quantities from raw inputs and previously defined quantities. Declare ALL shared parameters, including coefficients intended for the final response. Then expose any raw inputs you wish the final expression to use. Final expression can use exposed raw inputs, defined quantities, and parameters only. Full rewriting allowed. No new quantity required.',
    limits='At most 8 parameters and 8 quantities. Finite lower < initial < upper. Expressions <=1600 characters and 300 nodes. No observed response, row ids, per-row constants, slicing, comprehensions or arbitrary code.',
    experiment_interface='Up to four novel conditions: u [-1.1,1.1], h [0,2.5], history length four with values [-1,1]. Fixed times [-4,-3,-2,-1] and dt=1. Four repeats each. Only drives/waiting/response available; no internal-state sensor.')


def design_key(r):return tuple([r['u'],r['h'],*r['history'],*r['times'],r['dt']])


def acquire_for(candidate,seen,batch):
    dest=ROOT/'experiments'/f'batch_{batch}'
    if (dest/'OBSERVATIONS.json').exists():return read(dest/'OBSERVATIONS.json')['rows']
    known={design_key(r) for r in seen};designs=[];rejected=[]
    for i,r in enumerate(candidate['scaffold']['experiments'][:4]):
        try:
            vals=[r['u'],r['h'],*r['history']]
            assert len(r['history'])==4 and all(math.isfinite(v) for v in vals)
            assert -1.1<=r['u']<=1.1 and 0<=r['h']<=2.5 and all(-1<=v<=1 for v in r['history'])
            d=dict(u=r['u'],h=r['h'],history=r['history'],times=[-4.,-3.,-2.,-1.],dt=1.,design_id=f'b{batch}_{i}')
            assert design_key(d) not in known,'Previously observed or duplicate design'
            known.add(design_key(d));designs.append(d)
        except Exception as exc:rejected.append(dict(request=r,reason=str(exc) or 'Outside interface bounds'))
    model=Model(candidate['scaffold'],candidate['expression']);values=candidate['result']['values']
    predictions=model.predict(designs,values).tolist() if designs else []
    write(dest/'PREDICTION_FREEZE.json',dict(time=now(),candidate_id=candidate['id'],designs=designs,predictions=predictions,
          parameter_values=values,rejected_requests=rejected,candidate_sha256=sha(ROOT/'candidates'/(candidate['id']+'.json'))))
    rows=evaluator.acquire(designs,3103200+batch)
    rows=[dict(r,row_id=f'fresh_{batch}_{i}') for i,r in enumerate(rows)]
    write(dest/'OBSERVATIONS.json',dict(time=now(),rows=rows,prediction_sha256=sha(dest/'PREDICTION_FREEZE.json'),
          rmse=rmse(model.predict(rows,values),rows) if rows else None,
          scope='Prospective frozen-parameter prediction before acquisition; simulator development evidence'))
    return rows


def run():
    verify();evidence=read(ROOT/'visible/evidence.json');dev=list(evidence['dev']);train=evidence['fit']
    history=[];candidates=[];partial=None;stage='build';technical_repairs=0;completed_models=0;new_batches=0
    for index in range(1,7):
        bundle=dict(stage=stage,task='Discover a useful representation or complete response law from observed model failure. Explain what specific evidence motivates each change. A named latent quantity without acquisition or computation is insufficient.',
                    evidence=dict(metadata=evidence['metadata'],fit=train,dev=dev),language=LANGUAGE,
                    budget=dict(call_index=index,max_calls=6,max_parameter_fit_calls_per_candidate=1600,acceptance_rmse=.06),
                    prior_steps=history)
        if stage=='build':
            bundle['instruction']='Submit ONE PARTIAL construction, not a full response formula. Define your chosen quantities, all parameters, final exposed raw inputs and informative new experimental conditions. Use the raw observations and numerical feedback. The tool will test information capacity before you compose the final response.'
        else:
            bundle['partial_construction']=partial
            bundle['instruction']='Compose ONE complete response expression using only the allowed symbols in the supplied partial construction. Parameter and quantity definitions are fixed for this step. Use the named parameter binding and raw response units. Explain the scientific change and testable contrasts; these annotations do not override the equation.'
        reply=infer(index,stage,bundle)
        if stage=='build':
            def audit_build():
                try:
                    model=Model(reply);audit=capacity_audit(reply,dev,evidence['metadata'])
                    return dict(status='valid_partial',manifest=model.manifest(),capacity=audit,
                                response_valued_quantities=[q['name'] for q in reply['quantities'] if model.env[q['name']]==(0,(0,1))],
                                evidence_refs_valid=all(x in {r['row_id'] for r in train+dev} for x in reply['evidence_refs']))
                except Exception as exc:return dict(status='invalid_partial',error=str(exc))
            audit=cached(ROOT/'steps'/f'{index:02d}_build_audit.json',audit_build)
            history.append(dict(call=index,stage=stage,proposal=reply,tool_feedback=audit))
            if audit['status']=='invalid_partial':
                technical_repairs+=1
                if technical_repairs>1:break
                continue
            partial=reply
            stage='finish' if audit['capacity']['finish_enabled'] else 'build'
            technical_repairs=0
            print(json.dumps(dict(call=index,construction=audit)),flush=True)
        else:
            result=cached(ROOT/'steps'/f'{index:02d}_fit.json',lambda:fit(partial,reply['expression'],train,dev))
            cid=f'C{len(candidates)+1}'
            candidate=dict(id=cid,call=index,scaffold=partial,expression=reply['expression'],annotation=reply,
                           result=result,dev_row_ids=[r['row_id'] for r in dev])
            cached(ROOT/'candidates'/(cid+'.json'),lambda:candidate);candidates.append(candidate)
            history.append(dict(call=index,stage=stage,proposal=reply,tool_feedback=result))
            print(json.dumps(dict(call=index,candidate=cid,status=result['status'],fit_rmse=result.get('fit_rmse'),dev_rmse=result.get('dev_rmse'))),flush=True)
            if result['status']!='executed':
                technical_repairs+=1
                if technical_repairs>1:break
                continue
            completed_models+=1;technical_repairs=0;stage='build'
            if completed_models>=2 and new_batches<2:
                new_batches+=1;fresh=acquire_for(candidate,train+dev,new_batches)
                if index<6:dev+=fresh
                history[-1]['prospective_experiment']=read(ROOT/'experiments'/f'batch_{new_batches}'/'OBSERVATIONS.json')
    executed=[c for c in candidates if c['result']['status']=='executed']
    if executed and new_batches==0:
        new_batches=1;acquire_for(executed[-1],train+dev,1)
    # Re-score every frozen fit on the same FINAL development evidence, without refit.
    common=[]
    for c in executed:
        try:
            score=rmse(Model(c['scaffold'],c['expression']).predict(dev,c['result']['values']),dev)
            common.append(dict(id=c['id'],dev_rmse=score,converged=c['result']['optimizer_converged']))
        except Exception as exc:common.append(dict(id=c['id'],dev_rmse=None,converged=False,error=str(exc)))
    eligible=[r for r in common if r['dev_rmse'] is not None and r['dev_rmse']<=.06 and r['converged']]
    selected=min(eligible,key=lambda r:(r['dev_rmse'],r['id']))['id'] if eligible else None
    cached(ROOT/'SELECTION_FREEZE.json',lambda:dict(time=now(),selected=selected,common_development=common,
       development_row_ids=[r['row_id'] for r in dev],candidate_hashes={c['id']:sha(ROOT/'candidates'/(c['id']+'.json')) for c in candidates},hidden_read=False))
    hidden=read(ROOT/'evaluator_only/hidden.json');independent=[]
    for c in executed:
        try:
            score=rmse(Model(c['scaffold'],c['expression']).predict(hidden,c['result']['values']),hidden)
            independent.append(dict(id=c['id'],hidden_rmse=score,selected=c['id']==selected,
                                    independently_accepted=bool(c['id']==selected and score<=.06)))
        except Exception as exc:independent.append(dict(id=c['id'],error=str(exc),independently_accepted=False))
    cached(ROOT/'INDEPENDENT_RESULTS.json',lambda:dict(time=now(),results=independent,selection_sha256=sha(ROOT/'SELECTION_FREEZE.json'),hidden_sha256=sha(ROOT/'evaluator_only/hidden.json')))
    verify()
    summary=dict(time=now(),calls=len(list((ROOT/'calls').glob('*/reply.json'))),complete_proposals=len(candidates),
         executable_proposals=len(executed),construction_blocks=sum(x.get('tool_feedback',{}).get('capacity',{}).get('finish_enabled') is False for x in history),
         unambiguous_preformula_blocks=sum(x.get('tool_feedback',{}).get('capacity',{}).get('finish_enabled') is False and not x.get('tool_feedback',{}).get('response_valued_quantities') for x in history),
         selected=selected,independent=independent,common_development=common,prospective_batches=new_batches,
         residual_calls=sum(c['result'].get('residual_calls',0) for c in candidates),original_stage_hashes_unchanged=True,
         scientific_revisions=[dict(prior=executed[i-1]['id'],next=executed[i]['id'],prior_expression=executed[i-1]['expression'],next_expression=executed[i]['expression']) for i in range(1,len(executed))],
         scope='Controlled development recovery; no F/G efficacy estimate, no open-discovery or world-originality result')
    cached(ROOT/'SUMMARY.json',lambda:summary)
    print(json.dumps(summary,ensure_ascii=False),flush=True)


if __name__=='__main__':
    if sys.argv[1]=='prepare':prepare()
    elif sys.argv[1]=='run':run()
    elif sys.argv[1]=='verify':verify();print('Frozen sources and original stage hashes verified')
