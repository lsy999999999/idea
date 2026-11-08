"""Single frozen F/G pair with identical evidence and an actual route mask."""
import copy
import importlib.util
import json
import math
from pathlib import Path
import re
import sys
import numpy as np
from model_language import Model,fit,rmse
from structure_tools import additive_certificate,allowed_operations,assemble,membership

ROOT=Path(__file__).resolve().parent
PREVIOUS=ROOT.parent/'structure_search_recovery_20261103'
sys.path.append(str(PREVIOUS))
spec=importlib.util.spec_from_file_location('recovery_transport',PREVIOUS/'run.py')
e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)
e.ROOT=ROOT;e.STERILE=Path('/private/tmp/idea-composition-pilot-20261103-inference')
O=e.object_schema;A=e.array;S=e.S;N=e.N


def verify_history():
    for p,h in e.read(PREVIOUS/'RESULTS_SEAL.json')['files'].items():assert e.sha(PREVIOUS/p)==h,p
    e.verify()


def prepare():
    from checks import run
    for p,h in e.read(PREVIOUS/'RESULTS_SEAL.json')['files'].items():assert e.sha(PREVIOUS/p)==h,p
    e.write(ROOT/'IMPLEMENTATION_CHECKS.json',run())
    old=e.read(PREVIOUS/'amendment1/visible/evidence.json')
    old['dev']+=e.read(PREVIOUS/'amendment1/experiments/batch_1/OBSERVATIONS.json')['rows']
    previous=[]
    for cid in ['C5','C6']:
        c=e.read(PREVIOUS/'amendment1/candidates'/(cid+'.json'))
        m=Model(c['scaffold'],c['expression'])
        previous.append(dict(id=cid,quantities=c['scaffold']['quantities'],expression=c['expression'],
          fitted_parameters=c['result']['parameters'],dev_rmse=rmse(m.predict(old['dev'],c['result']['values']),old['dev'])))
    old['previous_failed_models']=previous
    e.write(ROOT/'visible/evidence.json',old)
    # New independent records from the same development mechanism.
    rng=np.random.default_rng(31103001)
    def design():return dict(u=float(rng.uniform(-1.1,1.1)),h=float(rng.uniform(0,2.5)),history=rng.uniform(-1,1,4).tolist(),times=[-4.,-3.,-2.,-1.],dt=1.)
    hidden=[design() for _ in range(160)];fixed=[dict(design(),source='fixed_confirmation',design_id='fixed_'+str(i)) for i in range(4)]
    e.write(ROOT/'evaluator_only/hidden.json',e.evaluator.acquire(hidden,31103002,1))
    e.write(ROOT/'confirmation_designs.json',fixed)
    partition_schema=O(dict(id=S,left=A(dict(type='string',enum=list(e.RAW)) if hasattr(e,'RAW') else dict(type='string',enum=['u','h','history','times','dt'])),right=A(dict(type='string',enum=['u','h','history','times','dt'])),reason=S,evidence_refs=A(S)))
    e.write(ROOT/'constraints_schema.json',O(dict(partitions=A(partition_schema,maxItems=3),remaining_uncertainties=A(S))))
    e.STERILE.mkdir(exist_ok=False)
    e.write(e.STERILE/'AGENTS.md','Answer only from the supplied serialized task. No tools, file access, memory, network, or delegation. Return the requested JSON directly.\n')
    files=['pilot.py','structure_tools.py','checks.py','model_language.py','PROTOCOL.md','IMPLEMENTATION_CHECKS.json',
       'visible/evidence.json','evaluator_only/hidden.json','confirmation_designs.json','constraints_schema.json',
       '../structure_search_recovery_20261103/run.py','../structure_search_recovery_20261103/evaluator.py',
       '../structure_search_recovery_20261103/RESULTS_SEAL.json']
    e.write(ROOT/'FROZEN.json',dict(time=e.now(),files={p:e.sha(ROOT/p) for p in files},
       prior_stage_files=e.read(PREVIOUS/'FROZEN.json')['prior_stage_files'],sterile_instructions_sha256=e.sha(e.STERILE/'AGENTS.md'),
       model='gpt-6-luna',effort='low',research_call_cap=5,fit_rows=len(old['fit']),dev_rows=len(old['dev'])))
    print(json.dumps(dict(prepared=True,fit_rows=len(old['fit']),dev_rows=len(old['dev']),checks=len(e.read(ROOT/'IMPLEMENTATION_CHECKS.json')))))


def shared_constraints(ev):
    bundle=dict(stage='propose structural partitions for verification',evidence=ev,
       task='Identify which retained additive-separation assumptions in the failed formulas may prevent explaining the observations. Propose at most three partitions of ALL five raw inputs into two disjoint nonempty groups. For each, the tool will compute the exact best empirical RMSE of every shared deterministic O=A(left)+B(right).',
       instructions='Use actual row_id references. Do not submit a replacement response formula, mechanism menu or a known answer. A failed fitted formula alone is not proof an entire class fails. It is valid to return no partitions if evidence is insufficient.',
       output_schema='partitions: id,left,right,reason,evidence_refs; remaining_uncertainties')
    proposals=e.infer(1,'constraints',bundle)
    def certify():
        verified=[];invalid=[];ids=set();visible_ids={r['row_id'] for r in ev['fit']+ev['dev']}
        for p in proposals['partitions']:
            try:
                if not re.fullmatch('[A-Za-z][A-Za-z0-9_]{0,15}',p['id']) or p['id'] in ids:raise ValueError('Invalid or duplicate partition id')
                ids.add(p['id'])
                cert=additive_certificate(ev['dev'],p,ev['metadata'])
                cert['proposal']=p;cert['evidence_refs_valid']=all(x in visible_ids for x in p['evidence_refs'])
                verified.append(cert)
            except Exception as exc:invalid.append(dict(proposal=p,error=str(exc)))
        return dict(time=e.now(),certificates=verified,invalid=invalid,proposal_sha256=e.sha(ROOT/'calls/01_constraints/reply.json'))
    certificate=e.cached(ROOT/'CONSTRAINT_CERTIFICATES.json',certify)
    valid=[c['proposal'] for c in certificate['certificates']]
    # Same compact scientific evidence for both arms; exact dual vectors remain
    # in the common accessible certificate artifact, not repeated in huge prompts.
    compact=[{k:v for k,v in c.items() if k!='dual_residual'} for c in certificate['certificates']]
    package=dict(proposals=proposals,verified=compact,invalid=certificate['invalid'],exact_certificate_sha256=e.sha(ROOT/'CONSTRAINT_CERTIFICATES.json'))
    if not (ROOT/'GENERATION_FREEZE.json').exists():
        for arm in ['F','G']:
            control=allowed_operations(valid,certificate['certificates'],arm)
            e.write(ROOT/'controls'/(arm+'.json'),control)
            e.write(ROOT/(arm+'_plan_schema.json'),O(dict(operation=dict(type='string',enum=control['allowed']),reason=S,evidence_refs=A(S))))
        e.write(ROOT/'SHARED_CONSTRAINT_PACKAGE.json',package)
        files=['CONSTRAINT_CERTIFICATES.json','SHARED_CONSTRAINT_PACKAGE.json','controls/F.json','controls/G.json','F_plan_schema.json','G_plan_schema.json']
        e.write(ROOT/'GENERATION_FREEZE.json',dict(time=e.now(),files={p:e.sha(ROOT/p) for p in files},complete_predictor_submitted=False))
    verify_generation()
    return valid,package


def verify_generation():
    for p,h in e.read(ROOT/'GENERATION_FREEZE.json')['files'].items():assert e.sha(ROOT/p)==h,p


def base_bundle(ev,package):
    language=copy.deepcopy(e.LANGUAGE)
    language['construction']='At complete-model submission, declare ALL parameters, sequential quantities, exposed inputs, and equation together. The earlier operation selection freezes no coefficients or quantity definitions. Full rewriting and no-new-quantity solutions remain available.'
    return dict(evidence=ev,constraint_package=package,language=language,
       resource_limits=dict(complete_candidates=1,parameters=8,quantities=8,actual_residual_calls=1600,dev_rmse_threshold=.06),
       scientific_goal='Define useful quantities or relationships and a complete response that explains the observed failure. Ground changes in evidence and propose informative executable new conditions. Prediction validity is distinct from unique mechanism identification.')


def plan(arm,index,ev,package,partitions):
    control=e.read(ROOT/'controls'/(arm+'.json'))
    bundle=base_bundle(ev,package)
    bundle.update(stage='choose one partial construction operation',construction_operations=control,
       instruction='Select exactly one permitted operation before submitting any equation. joint permits a whole response over any inputs. separate:P will be assembled as a sum of two branches each restricted to one side of partition P. Do not submit model formulas, parameter values, or quantity definitions at this stage. Later you can declare every needed shared coefficient in one complete specification.')
    reply=e.infer(index,arm+'_plan',bundle)
    if reply['operation'] not in control['allowed']:raise RuntimeError('Operation violated actual output schema; no silent recovery')
    file=ROOT/(arm+'_full_schema.json')
    if not file.exists():
        sc=copy.deepcopy(e.schemas()['build']);props=sc['properties']
        # Both branches use the same language. The actual constructor determines
        # the selected operation, not a label in a later natural-language report.
        if reply['operation']=='joint':props['expression']=S;sc['required'].append('expression')
        else:
            props.update(left_expression=S,right_expression=S);sc['required']+=['left_expression','right_expression']
        props['scientific_change']=S;sc['required'].append('scientific_change')
        e.write(file,sc)
        e.write(ROOT/'controls'/(arm+'_completion_freeze.json'),dict(time=e.now(),operation=reply['operation'],
             schema_sha256=e.sha(file),plan_sha256=e.sha(ROOT/'calls'/f'{index:02d}_{arm}_plan/reply.json'),complete_predictor_submitted=False))
    return reply


def complete(arm,index,ev,package,partitions,partial):
    verify_generation()
    freeze=e.read(ROOT/'controls'/(arm+'_completion_freeze.json'))
    assert e.sha(ROOT/(arm+'_full_schema.json'))==freeze['schema_sha256']
    bundle=base_bundle(ev,package)
    bundle.update(stage='submit one complete named model',chosen_partial_operation=partial,
       instruction='Submit one complete executable replacement. Declare all named shared parameters and their dimensions, all quantities, exposed raw inputs, and the required equation fields together. Final raw response dimension is [0,1]. Every symbol must be declared. evidence_refs must be actual row_ids. Propose up to four NEW conditions different from all supplied fit/dev rows; only drive, waiting time and response are available. Do not merely rename missing measurements.',
       completion_semantics='For joint use expression. For separate use left_expression and right_expression; tool checks their raw dependencies and adds them. Definitions may be shared but may not bypass branch dependencies.')
    raw=e.infer(index,arm+'_full',bundle)
    def evaluate():
        try:
            scaffold,expression,model=assemble(raw,partial['operation'],partitions)
            result=fit(scaffold,expression,ev['fit'],ev['dev'])
            classes=[dict(partition_id=c['id'],hard_excluded=c['hard_excluded'],**membership(model,c['left'],c['right'])) for c in e.read(ROOT/'CONSTRAINT_CERTIFICATES.json')['certificates']]
            return dict(arm=arm,operation=partial['operation'],raw=raw,scaffold=scaffold,expression=expression,result=result,
                       class_audits=classes,post_generation_certified_violation=any(c['hard_excluded'] and c['certified_additive'] for c in classes))
        except Exception as exc:return dict(arm=arm,operation=partial['operation'],raw=raw,result=dict(status='construction_failed',error=str(exc)))
    return e.cached(ROOT/'candidates'/(arm+'.json'),evaluate)


def select_and_test(candidates,ev):
    select=dict(time=e.now(),arms={c['arm']:dict(selected=bool(c['result'].get('dev_pass')),dev_rmse=c['result'].get('dev_rmse'),
                  status=c['result']['status'],candidate_sha256=e.sha(ROOT/'candidates'/(c['arm']+'.json'))) for c in candidates},
                hidden_read=False,new_observations_acquired=False)
    e.cached(ROOT/'SELECTION_FREEZE.json',lambda:select)
    designs=list(e.read(ROOT/'confirmation_designs.json'));seen={e.design_key(r) for r in ev['fit']+ev['dev']+designs};rejected=[]
    for c in candidates:
        for i,r in enumerate(c['raw']['experiments'][:4]):
            try:
                assert len(r['history'])==4 and all(math.isfinite(v) for v in [r['u'],r['h'],*r['history']])
                assert -1.1<=r['u']<=1.1 and 0<=r['h']<=2.5 and all(-1<=v<=1 for v in r['history'])
                d=dict(u=r['u'],h=r['h'],history=r['history'],times=[-4.,-3.,-2.,-1.],dt=1.,source=c['arm'],design_id=c['arm']+'_'+str(i))
                assert e.design_key(d) not in seen,'Already observed or duplicate request'
                seen.add(e.design_key(d));designs.append(d)
            except Exception as exc:rejected.append(dict(arm=c['arm'],request=r,error=str(exc) or 'Invalid interface bounds'))
    forecasts=[]
    for c in candidates:
        if c['result']['status']=='executed':
            try:
                predictions=Model(c['scaffold'],c['expression']).predict(designs,c['result']['values']).tolist()
                forecasts.append(dict(arm=c['arm'],predictions=predictions,values=c['result']['values']))
            except Exception as exc:forecasts.append(dict(arm=c['arm'],predictions=None,error=str(exc)))
        else:forecasts.append(dict(arm=c['arm'],predictions=None))
    e.cached(ROOT/'PREDICTION_FREEZE.json',lambda:dict(time=e.now(),designs=designs,forecasts=forecasts,rejected_requests=rejected,selection_sha256=e.sha(ROOT/'SELECTION_FREEZE.json')))
    e.cached(ROOT/'NEW_OBSERVATIONS.json',lambda:dict(time=e.now(),rows=e.evaluator.acquire(designs,31103003,4),prediction_sha256=e.sha(ROOT/'PREDICTION_FREEZE.json')))
    new=e.read(ROOT/'NEW_OBSERVATIONS.json')['rows'];fixed=[r for r in new if r['source']=='fixed_confirmation']
    hidden=e.read(ROOT/'evaluator_only/hidden.json');results=[]
    for c in candidates:
        result=dict(arm=c['arm'],status=c['result']['status'],dev_rmse=c['result'].get('dev_rmse'),accepted=False)
        if c['result']['status']=='executed':
            try:
                m=Model(c['scaffold'],c['expression']);values=c['result']['values']
                result.update(hidden_rmse=rmse(m.predict(hidden,values),hidden),fixed_confirmation_rmse=rmse(m.predict(fixed,values),fixed),all_prospective_rmse=rmse(m.predict(new,values),new))
                result['accepted']=bool(c['result']['dev_pass'] and result['hidden_rmse']<=.06 and result['fixed_confirmation_rmse']<=.06)
            except Exception as exc:result['error']=str(exc)
        results.append(result)
    return e.cached(ROOT/'INDEPENDENT_RESULTS.json',lambda:dict(time=e.now(),results=results,new_conditions=len(designs),new_observations=len(new),fixed_conditions=4,
       selection_sha256=e.sha(ROOT/'SELECTION_FREEZE.json'),prediction_sha256=e.sha(ROOT/'PREDICTION_FREEZE.json'),hidden_sha256=e.sha(ROOT/'evaluator_only/hidden.json')))


def run():
    verify_history();ev=e.read(ROOT/'visible/evidence.json')
    partitions,package=shared_constraints(ev)
    plans={}
    plans['F']=plan('F',2,ev,package,partitions)
    plans['G']=plan('G',3,ev,package,partitions)
    candidates=[complete('F',4,ev,package,partitions,plans['F']),complete('G',5,ev,package,partitions,plans['G'])]
    independent=select_and_test(candidates,ev)
    verify_history();verify_generation()
    usage={}
    for p in (ROOT/'calls').glob('*/completion_*.json'):
        item=e.read(p)
        assert not item['tool_violations']
        for k,v in item['usage'].items():usage[k]=usage.get(k,0)+v
    summary=dict(time=e.now(),research_calls=len(list((ROOT/'calls').glob('*/reply.json'))),proposed_partitions=len(e.read(ROOT/'calls/01_constraints/reply.json')['partitions']),
        hard_certificates=sum(c['hard_excluded'] for c in e.read(ROOT/'CONSTRAINT_CERTIFICATES.json')['certificates']),
        plans=plans,controls={a:e.read(ROOT/'controls'/(a+'.json')) for a in ['F','G']},
        candidates=[dict(arm=c['arm'],operation=c['operation'],expression=c.get('expression'),status=c['result']['status'],
                        class_violation=c.get('post_generation_certified_violation'),residual_calls=c['result'].get('residual_calls',0)) for c in candidates],
        independent=independent,usage=usage,
        interpretation='One controlled development pair. Actual route masks and full candidate class violations are separate. No average F/G advantage or open-structure discovery established by this sample.')
    e.cached(ROOT/'SUMMARY.json',lambda:summary)
    print(json.dumps(summary,ensure_ascii=False),flush=True)


if __name__=='__main__':
    if sys.argv[1]=='prepare':prepare()
    elif sys.argv[1]=='run':run()
