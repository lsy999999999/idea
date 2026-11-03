"""Frozen stage-one harness. Researchers only see serialized bundles, never this file."""
import ast
import datetime as dtm
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import numpy as np
from scipy.optimize import least_squares

ROOT = Path(__file__).resolve().parent
CLI = '/opt/homebrew/bin/codex'

def now(): return dtm.datetime.now(dtm.timezone.utc).isoformat()
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text())
def write(p, obj):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('x') as f:
        f.write(obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False))
def event(kind, **kw):
    with (ROOT/'EVENTS.jsonl').open('a') as f:
        f.write(json.dumps(dict(time=now(),kind=kind,**kw),ensure_ascii=False)+'\n')

def truth(row):
    y = np.sum(np.array(row['history'])*np.exp(np.array(row['times'])/2.2))*row['dt']
    return float(.7*row['u']+.3*row['u']**3+.8*y*np.exp(-row['h']/2.2))

def design(u,h,history):
    return dict(u=float(u),h=float(h),history=list(map(float,history)),times=[-4.,-3.,-2.,-1.],dt=1.)

def observed(rows, seed):
    rng=np.random.default_rng(seed)
    return [dict(r, o=truth(r)+float(rng.uniform(-.015,.015))) for r in rows]

def prepare():
    rng=np.random.default_rng(4021)
    train=[]
    for i in range(36):
        train.append(design([-.8,.1,.9][i%3],[.2,.9,1.6][(i//3)%3],rng.uniform(-1,1,4)))
    diag=[]
    for h in [.3,1.2]:
        for hist in [[1,1,1,1],[-1,-1,-1,-1]]:
            for rep in range(6):
                diag.append(dict(design(.4,h,hist),repeat=rep))
    fit=observed(train,4022);dev=observed(diag,4023)
    hidden=observed([design(rng.uniform(-1.1,1.1),rng.uniform(0,2.5),rng.uniform(-1,1,4)) for _ in range(128)],9041)
    catalog=[]
    for i,hi in enumerate([[1,0,0,0],[0,0,0,1],[1,-1,1,-1],[-1,1,-1,1],[.5,.5,.5,.5]]):
        for h in [.5,2.2]:
            catalog.append(dict(id=f'E{len(catalog)+1}',**design(.65,h,hi),sensor_protocol='independently calibrated reference channel'))
    a=np.array([[1,r['u'],r['h']] for r in fit]);b=np.array([r['o'] for r in fit])
    p=np.linalg.lstsq(a,b,rcond=None)[0]
    rmse=lambda rows:float(np.sqrt(np.mean([(p@[1,r['u'],r['h']]-r['o'])**2 for r in rows])))
    gaps=[]
    for h in [.3,1.2]:
        one=[r['o'] for r in dev if r['h']==h and r['history'][0]==1]
        two=[r['o'] for r in dev if r['h']==h and r['history'][0]==-1]
        gaps.append(dict(u=.4,h=h,group1_mean=float(np.mean(one)),group2_mean=float(np.mean(two)),mean_gap=float(np.mean(one)-np.mean(two)),minimum_pair_gap=float(min(one)-max(two)),n1=6,n2=6))
    metadata=dict(units=dict(u='dimensionless drive',h='s',history='dimensionless drive',times='s relative to current time',dt='s',o='response units'),history_order='oldest to newest; interval of length dt ending at each times entry',prediction_time='u,h and full prior drive record available before response o; o unavailable',noise_bound=.015,matching='u and h are exact controlled values; histories intentionally differ',shared_parameters=True,deterministic_response_assumption=True,measurement_stable=True,measurement_certificate='Evaluator supplies calibrated identical reference channel; absolute readout error bounded by 0.015 response units. Conditional development assumption, not inferred from repeated data.',fit_rule='refit all parameters on fit only; dev separate; all targets raw o',old_model='o=p[0]+p[1]*u+p[2]*h',old_model_fit=p.tolist(),old_model_fit_rmse=rmse(fit),old_model_dev_rmse=rmse(dev),old_model_optimizer='unconstrained linear least squares global minimizer')
    visible=dict(task='Explain the current model failure, define any useful quantities and a complete executable replacement, or request missing information. No new quantity is compulsory. Distinguish prediction from mechanism identification.',metadata=metadata,fit=fit,dev=dev,diagnostics=gaps,experiment_catalog=catalog)
    write(ROOT/'visible/evidence.json',visible)
    write(ROOT/'evaluator_only/hidden.json',hidden)
    write(ROOT/'evaluator_only/ground_truth.json',dict(expression='0.7*u+0.3*u**3+0.8*sum(history*exp(times/2.2))*dt*exp(-h/2.2)',scope='Controlled development task; never included in research inputs',train_seed=4022,hidden_seed=9041))
    files=[ROOT/'experiment.py',ROOT/'PROTOCOL.md',ROOT/'visible/evidence.json',ROOT/'evaluator_only/hidden.json',ROOT/'evaluator_only/ground_truth.json']
    write(ROOT/'FROZEN_DESIGN.json',dict(time=now(),files={str(p.relative_to(ROOT)):sha(p) for p in files},model='gpt-6-luna',reasoning_effort='low',max_candidates_per_arm=3,max_successful_calls=6))
    event('design_frozen',sha256=sha(ROOT/'FROZEN_DESIGN.json'))
    print(json.dumps(dict(prepared=True,fit_rows=len(fit),dev_rows=len(dev),hidden_rows=len(hidden),old_model_dev_rmse=rmse(dev),gaps=gaps)))

def verify_design():
    for p,h in read(ROOT/'FROZEN_DESIGN.json')['files'].items(): assert sha(ROOT/p)==h,p

def infer(label, bundle):
    verify_design()
    calls=ROOT/'calls';calls.mkdir(exist_ok=True)
    assert len(list(calls.glob('*/reply.json')))<6
    dest=calls/label
    prompt='Controlled research inference. Use only the JSON bundle below. No tools, files, memory, network, delegation or other conversations. Respond directly with one JSON object.\n'+json.dumps(bundle,ensure_ascii=False)
    if not dest.exists():
        dest.mkdir();write(dest/'input.json',bundle);write(dest/'prompt.txt',prompt)
    else: assert read(dest/'input.json')==bundle
    if (dest/'reply.json').exists(): return read(dest/'reply.json')
    for attempt in range(2):
        if (dest/f'completion_{attempt}.json').exists():
            if read(dest/f'completion_{attempt}.json')['returncode']!=0: continue
            raise RuntimeError('A completed output exists without sealed reply; manual format audit required')
        cmd=[CLI,'exec','--ephemeral','--skip-git-repo-check','--model','gpt-6-luna','-c','model_reasoning_effort="low"','--sandbox','read-only','--color','never','--json','--output-last-message',str(dest/f'output_{attempt}.txt'),'-C',str(ROOT),'-']
        write(dest/f'command_{attempt}.json',cmd)
        event('inference_started',label=label,attempt=attempt,input_sha256=sha(dest/'input.json'))
        started=time.monotonic()
        with (dest/f'events_{attempt}.jsonl').open('x') as out,(dest/f'stderr_{attempt}.txt').open('x') as err:
            try: result=subprocess.run(cmd,input=prompt,text=True,stdout=out,stderr=err,timeout=600);rc=result.returncode
            except subprocess.TimeoutExpired:rc=124
        usage={};violations=[]
        for line in (dest/f'events_{attempt}.jsonl').read_text().splitlines():
            try:e=json.loads(line)
            except json.JSONDecodeError:continue
            if e.get('type')=='turn.completed':usage=e.get('usage',{})
            if e.get('item',{}).get('type') in ['command_execution','mcp_tool_call','web_search','file_change']:
                violations.append(e['item']['type'])
        write(dest/f'completion_{attempt}.json',dict(time=now(),returncode=rc,seconds=time.monotonic()-started,usage=usage,tool_violations=violations,requested_model='gpt-6-luna',requested_reasoning='low',backend_weight_independently_verified=False))
        event('inference_finished',label=label,attempt=attempt,returncode=rc)
        if violations: raise RuntimeError('Inference accessed tools')
        if rc: raise RuntimeError(f'Transport failed rc={rc}; rerun identical command after network permission if necessary')
        raw=(dest/f'output_{attempt}.txt').read_text().strip()
        raw=re.sub(r'^```(?:json)?\s*','',raw);raw=re.sub(r'\s*```$','',raw)
        reply=json.loads(raw)
        write(dest/'reply.json',reply);write(dest/'SEALED.json',dict(input_sha256=sha(dest/'input.json'),reply_sha256=sha(dest/'reply.json'),time=now()))
        return reply
    raise RuntimeError('Transport retry budget exhausted')

def constraint_call():
    evidence=read(ROOT/'visible/evidence.json')
    bundle=dict(stage='independent constraint derivation',evidence=evidence,mathematical_library='A deterministic single-valued function predicts one value for identical arguments and shared parameters. With two additive errors each bounded by epsilon, the observed gap cannot exceed 2*epsilon. This does not identify any physical mechanism.',instruction='Propose constraints from actual records. State precisely which joint assumptions are rejected, check premises, preserve alternative explanations, and supply pre-generation operations and withdrawal rules. Never equate fitted parameter failure to a whole-family impossibility.',output_schema=dict(constraints=[dict(id='string',rule='same_input_single_value or heuristic',evidence_refs=['specific records or diagnostics'],premises=['explicit strings'],derivation='mathematical argument and actual inequality',scope='exact excluded dependency class and assumptions',strength='hard or soft or none',generator_operation='concrete language/operation/budget change',independent_test='how each candidate is checked',withdrawal='which premise failure restores the search')],retrieval_queries=['at most two targeted queries on nearest methods and state representation'],unresolved_explanations=['strings']))
    result=infer('01_constraints',bundle)
    write(ROOT/'CONSTRAINT_PROPOSALS.json',result)
    audit=verify_constraints(result,evidence)
    write(ROOT/'CONSTRAINT_AUDIT.json',audit)
    print(json.dumps(audit,ensure_ascii=False))

def verify_constraints(proposals,evidence):
    md=evidence['metadata'];checks=dict(exact_current_inputs=md['matching'].startswith('u and h are exact'),shared_parameters=md['shared_parameters'],deterministic=md['deterministic_response_assumption'],measurement_stable=md['measurement_stable'],known_bounded_error=md['noise_bound']==.015)
    gaps=[]
    for h in sorted(set(r['h'] for r in evidence['dev'])):
        rows=[r for r in evidence['dev'] if r['h']==h]
        gaps.append(max(r['o'] for r in rows)-min(r['o'] for r in rows))
    supported=all(checks.values()) and max(gaps)>2*md['noise_bound']
    accepted=[];unverified=[]
    for c in proposals.get('constraints',[]):
        if c.get('rule')=='same_input_single_value' and supported:
            accepted.append(dict(original=c,verified_rule='single_value_collision',certified_scope='shared deterministic o=g(u,h) with common stable observation and bounded error; histories/extra information remain unrestricted',strength='hard',witness_gap=max(gaps),allowed_gap=2*md['noise_bound'],source='LLM proposal verified against mathematical rule and actual records'))
        else:unverified.append(dict(original=c,strength='soft',reason='No applicable executable certificate or premise failed'))
    return dict(time=now(),premise_checks=checks,certified=accepted,unverified=unverified,numerical_fit_failure_used_as_proof=False)

FUNCS={'sum':np.sum,'mean':np.mean,'exp':np.exp,'log':np.log,'sqrt':np.sqrt,'abs':np.abs,'sin':np.sin,'cos':np.cos,'tanh':np.tanh,'pow':np.power}
def parse_expr(expression,names):
    tree=ast.parse(expression,mode='eval')
    allowed=(ast.Expression,ast.BinOp,ast.UnaryOp,ast.Call,ast.Name,ast.Load,ast.Constant,ast.Subscript,ast.Add,ast.Sub,ast.Mult,ast.Div,ast.Pow,ast.USub,ast.UAdd)
    for n in ast.walk(tree):
        if not isinstance(n,allowed):raise ValueError('Unsupported mathematical syntax '+type(n).__name__)
        if isinstance(n,ast.Name) and n.id not in names|set(FUNCS):raise ValueError('Unknown symbol '+n.id)
        if isinstance(n,ast.Call) and (not isinstance(n.func,ast.Name) or n.func.id not in FUNCS):raise ValueError('Unsupported function')
        if isinstance(n,ast.Constant) and not isinstance(n.value,(float,int)):raise ValueError('Only numeric constants')
    return compile(tree,'<candidate>','eval')

def predictor(candidate):
    names={'u','h','history','times','dt','p'}
    quantities=[]
    for q in candidate.get('quantities',[]):
        name=q['name'];assert re.fullmatch('[A-Za-z][A-Za-z0-9_]*',name) and name not in names|set(FUNCS)
        quantities.append((name,parse_expr(q['expression'],names)));names.add(name)
    equation=parse_expr(candidate['expression'],names)
    def predict(rows,p):
        vals=[]
        with np.errstate(all='ignore'):
            for r in rows:
                env=dict(FUNCS,u=r['u'],h=r['h'],history=np.array(r['history']),times=np.array(r['times']),dt=r['dt'],p=p)
                for name,code in quantities:env[name]=eval(code,{'__builtins__':{}},env)
                v=float(eval(equation,{'__builtins__':{}},env))
                if not np.isfinite(v):raise ValueError('Nonfinite prediction')
                vals.append(v)
        return np.array(vals)
    return predict

def generator_config(arm,audit):
    base=dict(arm=arm,raw_proposal_cap=3,full_rewrite=True,parameters_only=True,extra_information_requests=True,language='composable scalar expressions over u,h,history,times,dt and p; sequential defined quantities; no mechanism menu',screening='same numerical and structural candidate tests')
    if arm=='G' and audit['certified']:
        base.update(parameters_only=False,disabled_operations=['rewrite shared deterministic g(u,h) while keeping current inputs and stable observation unchanged'],proposal_slots=[dict(slot=1,operation='construct information from previously recorded inputs'),dict(slot=2,operation='rewrite observation or obtain additional observable information'),dict(slot=3,operation='complete model rewrite using any distinguishing information consistent with certified scope')],budget_change='All 3 raw proposal slots reserved before inference for revisions outside the certified conflicting dependency class; no candidate removed to obtain this allocation',constraint_ids=[x['original']['id'] for x in audit['certified']])
    else:base.update(disabled_operations=[],proposal_slots=[dict(slot=i,operation='free parameter/structure/representation/measurement revision') for i in [1,2,3]],budget_change='No mandatory routing')
    return base

def generation_call(arm):
    ev=read(ROOT/'visible/evidence.json');audit=read(ROOT/'CONSTRAINT_AUDIT.json')
    config=generator_config(arm,audit);write(ROOT/f'configs/{arm}.json',config)
    package=dict(raw=read(ROOT/'CONSTRAINT_PROPOSALS.json'),audit=audit)
    literature=read(ROOT/'LITERATURE_BUNDLE.json') if (ROOT/'LITERATURE_BUNDLE.json').exists() else dict(sources=[],status='unavailable')
    schema=dict(candidates=[dict(id='C1/C2/C3',operation='what revision was made',quantities=[dict(name='Y',expression='scalar expression; history and times are numpy arrays, sum(history*exp(times/p[0])) permitted',units='unit',availability='before response',initialization_and_future='how window is initialized and used for future prediction')],expression='complete scalar response expression',parameters=[dict(name='parameter',unit='unit',initial=1.,lower=.05,upper=10.)],measurement_request='null or a specific executable acquisition with competing predictions; absent inputs cannot be fabricated',scope='prediction vs mechanism; alternatives',distinguishing_experiment='catalog ids and prediction relation')],selected_experiment_ids=['up to 8 catalog ids'],scientific_notes='brief')
    bundle=dict(stage='one bounded model revision',evidence=ev,constraint_package=package,retrieval_materials=literature,generator_config=config,language=dict(primitives=list(FUNCS),variables=['u','h','history','times','dt','p'],parameter_index='p[0]...; at most 4 shared fitted parameters per model, with finite bounds and interior initial values',restrictions='No row id, repeat id, o, hidden observations or per-sample fitted constants. No list comprehensions, slicing, attribute accesses or arbitrary code. Each new quantity defined before use. All parameter fitting uses fit only. A missing-measurement candidate may return null expression and is counted as an information request.'),instruction='Submit exactly 3 original complete candidate objects. Follow any assigned proposal_slots in order. F may freely use all constraint information. G uses the compiled operation allocation. Units, initialization and future prediction required. You can completely replace the old formula. Do not encode a new quantity by merely naming missing information. Choose new experiments from catalog before seeing observations. Output exactly the schema; no executable tools.',output_schema=schema)
    result=infer('02_generate_'+arm,bundle)
    write(ROOT/f'candidates/{arm}_raw.json',result)
    event('raw_candidates_saved',arm=arm,sha256=sha(ROOT/f'candidates/{arm}_raw.json'),count=len(result.get('candidates',[])))
    print(json.dumps(dict(arm=arm,candidates=len(result.get('candidates',[])),expressions=[c.get('expression') for c in result.get('candidates',[])]),ensure_ascii=False))

def fit_candidate(c,ev):
    if not c.get('expression'):return dict(status='measurement_request',request=c.get('measurement_request'),prediction_valid=False)
    try:
        pars=c.get('parameters',[]);assert len(pars)<=4
        pred=predictor(c);y=np.array([r['o'] for r in ev['fit']]);evaluations=0
        def residual(p):
            nonlocal evaluations
            evaluations+=1
            try:return pred(ev['fit'],p)-y
            except (ValueError,OverflowError,ZeroDivisionError):return np.full(len(y),1e6)
        if pars:
            lo=np.array([p['lower'] for p in pars],float);hi=np.array([p['upper'] for p in pars],float);initial=np.array([p['initial'] for p in pars],float)
            assert np.all(np.isfinite(lo)) and np.all(np.isfinite(hi)) and np.all(lo<initial) and np.all(initial<hi)
            starts=[initial,lo+.25*(hi-lo),lo+.5*(hi-lo),lo+.75*(hi-lo)]
            fits=[]
            for p0 in starts:
                counter=[0]
                def bounded_residual(p):
                    counter[0]+=1
                    if counter[0]>350:raise RuntimeError('fit residual call cap')
                    return residual(p)
                try:
                    f=least_squares(bounded_residual,p0,bounds=(lo,hi),max_nfev=70)
                    fits.append((float(np.sum((pred(ev['fit'],f.x)-y)**2)),f.x.tolist(),bool(f.success)))
                except (RuntimeError,ValueError,OverflowError,ZeroDivisionError):continue
            if not fits:raise ValueError('No finite fitted parameter vector found')
            _,p,converged=min(fits)
        else:p=[];converged=True
        train=pred(ev['fit'],p);dev=pred(ev['dev'],p)
        # Semantic classification uses actual response dependence, not quantity names.
        witnesses=[]
        for h in [.3,1.2]:
            pair=[design(.4,h,[1,1,1,1]),design(.4,h,[-1,-1,-1,-1])]
            witnesses.append(float(abs(np.diff(pred(pair,p))[0])))
        structural_violation=all(x<1e-10 for x in witnesses)
        train_rmse=float(np.sqrt(np.mean((train-y)**2)));dev_rmse=float(np.sqrt(np.mean((dev-np.array([r['o'] for r in ev['dev']]))**2)))
        return dict(status='executed',parameters=p,fit_rmse=train_rmse,dev_rmse=dev_rmse,optimizer_converged=converged,residual_evaluations=evaluations,observed_history_prediction_gaps=witnesses,structural_violation=structural_violation,semantic_classification_scope='Zero response difference on two witnessed history pairs; not exhaustive program-equivalence proof',dev_accepted=dev_rmse<=.06 and not structural_violation,prediction_valid=True)
    except Exception as exc:return dict(status='failed',error=str(exc),prediction_valid=False)

def evaluate():
    ev=read(ROOT/'visible/evidence.json');results={};selection={}
    for arm in ['F','G']:
        raw=read(ROOT/f'candidates/{arm}_raw.json');items=raw.get('candidates',[]);assert len(items)==3
        results[arm]=[]
        for i,c in enumerate(items):
            out=fit_candidate(c,ev);out.update(index=i,id=c.get('id'),raw_sha256=hashlib.sha256(json.dumps(c,sort_keys=True).encode()).hexdigest())
            results[arm].append(out)
        viable=[r for r in results[arm] if r.get('dev_accepted')]
        if viable:selection[arm]=min(viable,key=lambda r:r['dev_rmse'])['index']
        else:selection[arm]=None
    write(ROOT/'DEVELOPMENT_RESULTS.json',results)
    write(ROOT/'SELECTION_FREEZE.json',dict(time=now(),selection=selection,rule='lowest dev RMSE among executed dev-accepted candidates; hidden not yet loaded',candidates_sha256={a:sha(ROOT/f'candidates/{a}_raw.json') for a in ['F','G']},development_sha256=sha(ROOT/'DEVELOPMENT_RESULTS.json')))
    event('selection_frozen',sha256=sha(ROOT/'SELECTION_FREEZE.json'))
    # Freeze forecasts for the union of pre-submitted requests, before observations.
    catalog={r['id']:r for r in ev['experiment_catalog']};ids=[]
    for arm in ['F','G']:
        proposed=read(ROOT/f'candidates/{arm}_raw.json').get('selected_experiment_ids',[])[:8]
        for i in proposed:
            if i in catalog and i not in ids:ids.append(i)
    ids=ids[:8];exp_rows=[catalog[i] for i in ids]
    forecasts={}
    for arm in ['F','G']:
        forecasts[arm]=[];items=read(ROOT/f'candidates/{arm}_raw.json')['candidates']
        for c,r in zip(items,results[arm]):
            forecasts[arm].append(dict(id=c['id'],predictions=predictor(c)(exp_rows,r['parameters']).tolist()) if r['prediction_valid'] else dict(id=c['id'],predictions=None))
    write(ROOT/'PREDICTION_FREEZE.json',dict(time=now(),designs=exp_rows,predictions=forecasts,selection_sha256=sha(ROOT/'SELECTION_FREEZE.json')))
    event('prediction_frozen',sha256=sha(ROOT/'PREDICTION_FREEZE.json'))
    new=observed([dict(r,repeat=k) for r in exp_rows for k in range(4)],7103)
    write(ROOT/'NEW_EXPERIMENT.json',dict(time=now(),prediction_freeze_sha256=sha(ROOT/'PREDICTION_FREEZE.json'),rows=new,noise_bound=.015,measurement_protocol='Same response units, independent calibrated reference channel; reference and original agree within absolute readout bounds',prior_observations_used_for_fitting=False))
    event('new_evidence_obtained',sha256=sha(ROOT/'NEW_EXPERIMENT.json'))
    hidden=read(ROOT/'evaluator_only/hidden.json');scored={}
    for arm in ['F','G']:
        scored[arm]=[]
        for c,r in zip(read(ROOT/f'candidates/{arm}_raw.json')['candidates'],results[arm]):
            rec=dict(id=c['id'],index=r['index'],selected=selection[arm]==r['index'])
            if r['prediction_valid']:
                pred=predictor(c);p=r['parameters']
                rec['hidden_rmse']=float(np.sqrt(np.mean((pred(hidden,p)-np.array([v['o'] for v in hidden]))**2)))
                rec['new_experiment_rmse']=float(np.sqrt(np.mean((pred(new,p)-np.array([v['o'] for v in new]))**2))) if new else None
                rec['independently_valid']=r['dev_accepted'] and rec['hidden_rmse']<=.06
            else:rec['independently_valid']=False
            scored[arm].append(rec)
    write(ROOT/'INDEPENDENT_RESULTS.json',dict(time=now(),selection_freeze_sha256=sha(ROOT/'SELECTION_FREEZE.json'),prediction_freeze_sha256=sha(ROOT/'PREDICTION_FREEZE.json'),new_experiment_sha256=sha(ROOT/'NEW_EXPERIMENT.json'),hidden_sha256=sha(ROOT/'evaluator_only/hidden.json'),results=scored))
    print(json.dumps(dict(development=results,selection=selection,independent=scored),ensure_ascii=False))

def withdrawal():
    ev=read(ROOT/'visible/evidence.json');proposals=read(ROOT/'CONSTRAINT_PROPOSALS.json')
    ev['metadata']['measurement_stable']=False
    ev['metadata']['measurement_certificate']='WITHDRAWN in a counterfactual premise audit: instrument offsets may depend on preparation history; no reference bound available.'
    write(ROOT/'withdrawal/evidence_v2.json',ev)
    audit=verify_constraints(proposals,ev);write(ROOT/'withdrawal/constraint_audit_v2.json',audit)
    config=generator_config('G',audit);write(ROOT/'withdrawal/generator_v2.json',config)
    # Explicit feasible alternative under the changed assumption: constant system plus sensor offset.
    ref=read(ROOT/'visible/evidence.json');offsets={}
    for row in ref['dev']:
        key=json.dumps([row['u'],row['h'],row['history']])
        offsets.setdefault(key,[]).append(row['o'])
    means={k:float(np.mean(v)) for k,v in offsets.items()}
    errors=[abs(row['o']-means[json.dumps([row['u'],row['h'],row['history']])]) for row in ref['dev']]
    result=dict(type='organizer-controlled premise invalidation test, not a fresh scientific discovery',original_evidence_unchanged=True,active_hard_constraints=len(audit['certified']),current_only_rewrite_restored='rewrite shared deterministic g(u,h) while keeping current inputs and stable observation unchanged' not in config['disabled_operations'],parameters_only_restored=config['parameters_only'],counterexample='Underlying system o_true=0; preparation-dependent instrument offset equals the condition mean. This reproduces observed differences once stable observation is dropped.',counterexample_max_error=max(errors),noise_bound=.015,counterexample_feasible=max(errors)<=.015,scope='Finite diagnostic records only; counterexample establishes necessity of observation premise, not a general scientific explanation')
    assert result['active_hard_constraints']==0 and result['parameters_only_restored'] and result['counterexample_feasible']
    write(ROOT/'withdrawal/RESULT.json',result)
    event('constraint_withdrawn_on_premise_failure',config_sha256=sha(ROOT/'withdrawal/generator_v2.json'))
    print(json.dumps(result,ensure_ascii=False))

def final_call():
    b=dict(stage='scientific update after frozen forecasts and new evidence',initial_evidence=read(ROOT/'visible/evidence.json'),constraints=read(ROOT/'CONSTRAINT_AUDIT.json'),candidates={a:read(ROOT/f'candidates/{a}_raw.json') for a in ['F','G']},development=read(ROOT/'DEVELOPMENT_RESULTS.json'),forecast=read(ROOT/'PREDICTION_FREEZE.json'),new_evidence=read(ROOT/'NEW_EXPERIMENT.json'),withdrawal_test=read(ROOT/'withdrawal/RESULT.json'),instruction='Update the constraint from real new reference-channel evidence. Separately assess the explicitly counterfactual withdrawal test. Do not refit candidates, redefine thresholds or propose untested claims of method superiority. Classify variable usefulness, prediction support and remaining mechanism equivalence. Hidden final test results are not supplied.',output_schema=dict(constraint_decision='retain or soften or withdraw with rationale',evidence_refs=['specific evidence'],candidate_conclusions=['prediction and variable claims'],remaining_equivalent_explanations=['strings'],next_discriminating_action='concrete',stage1_acceptance='passed/partial/failed with conditions'))
    write(ROOT/'SCIENTIFIC_UPDATE.json',infer('03_update',b))
    print(json.dumps(read(ROOT/'SCIENTIFIC_UPDATE.json'),ensure_ascii=False))

def audit_final():
    verify_design()
    dev=read(ROOT/'DEVELOPMENT_RESULTS.json');ind=read(ROOT/'INDEPENDENT_RESULTS.json');pred=read(ROOT/'PREDICTION_FREEZE.json')
    checks={}
    for a in ['F','G']:
        inp=read(ROOT/f'calls/02_generate_{a}/input.json');checks[a+'_no_truth']=not any(k in json.dumps(inp) for k in ['0.7*u+0.3*u**3','ground_truth.json','hidden.json'])
    f=read(ROOT/'calls/02_generate_F/input.json');g=read(ROOT/'calls/02_generate_G/input.json')
    for key in ['evidence','constraint_package','retrieval_materials','language','output_schema','instruction']:checks['same_'+key]=f[key]==g[key]
    checks['pre_generation_config_changed']=f['generator_config']!=g['generator_config']
    checks['forecasts_bound_to_new_evidence']=sha(ROOT/'PREDICTION_FREEZE.json')==read(ROOT/'NEW_EXPERIMENT.json')['prediction_freeze_sha256']
    checks['selection_bound_to_hidden_scores']=sha(ROOT/'SELECTION_FREEZE.json')==ind['selection_freeze_sha256']
    checks['all_raw_proposals_counted']=all(len(dev[a])==3 for a in ['F','G'])
    checks['withdrawal_restores_operations']=read(ROOT/'withdrawal/RESULT.json')['parameters_only_restored']
    # Expression evaluator semantic regression independent of any submitted candidate.
    probe=dict(quantities=[dict(name='Y',expression='sum(history*exp(times/p[0]))*dt*exp(-h/p[0])')],expression='p[1]*u+p[2]*u**3+p[3]*Y')
    probe_rows=read(ROOT/'visible/evidence.json')['fit']
    checks['units_time_column_parameter_semantics']=float(np.max(np.abs(predictor(probe)(probe_rows,[2.2,.7,.3,.8])-np.array([truth(r) for r in probe_rows]))))<1e-12
    usage={};calls=[]
    for p in sorted((ROOT/'calls').glob('*/completion_*.json')):
        c=read(p);calls.append(dict(label=p.parent.name,**c))
        for k,v in c['usage'].items():
            if isinstance(v,(int,float)):usage[k]=usage.get(k,0)+v
    summary=dict(time=now(),checks=checks,passed=all(checks.values()),actual_completed_calls=sum(c['returncode']==0 for c in calls),actual_attempts=len(calls),usage=usage,model='gpt-6-luna',reasoning='low',model_weight_identity_independently_verified=False,results={a:dict(raw_proposals=3,execution_failures=sum(r['status']=='failed' for r in dev[a]),post_generation_structural_violations=sum(r.get('structural_violation',False) for r in dev[a]),dev_accepted=sum(r.get('dev_accepted',False) for r in dev[a]),independently_valid=sum(r.get('independently_valid',False) for r in ind['results'][a]),selected=read(ROOT/'SELECTION_FREEZE.json')['selection'][a]) for a in ['F','G']})
    write(ROOT/'FINAL_AUDIT.json',summary)
    assert summary['passed']
    write(ROOT/'FROZEN_RESULTS.json',dict(time=now(),files={str(p.relative_to(ROOT)):sha(p) for p in sorted(ROOT.rglob('*')) if p.is_file() and '__pycache__' not in str(p)}))
    print(json.dumps(summary,ensure_ascii=False))

if __name__=='__main__':
    action=sys.argv[1]
    if action=='prepare':prepare()
    elif action=='constraint':constraint_call()
    elif action=='generate':generation_call(sys.argv[2])
    elif action=='evaluate':evaluate()
    elif action=='withdrawal':withdrawal()
    elif action=='update':final_call()
    elif action=='audit':audit_final()
