import json
from pathlib import Path
import sys
import numpy as np

HERE=Path(__file__).resolve().parent
PARENT=HERE.parent
sys.path.insert(0,str(PARENT))
import run as e
from model_language import Model, fit, capacity_audit, rmse


def prepare():
    # Original attempt is frozen, not patched.
    e.verify()
    old_summary=e.read(PARENT/'SUMMARY.json');assert old_summary['calls']==4
    schema=e.schemas()['build'];schema['properties']['expression']=e.S
    schema['properties']['scientific_change']=e.S
    schema['required']+=['expression','scientific_change']
    e.write(HERE/'full_schema.json',schema)
    # Regression: a jointly declared response coefficient restores a well-typed
    # complete program. This is a generic interface fixture, never research input.
    fixture=dict(parameters=[dict(name='coefficient',dimension=[0,1],lower=-4.,initial=1.,upper=4.)],quantities=[],exposed_inputs=['u'])
    row=dict(u=.5,h=.3,history=[0.,0.,0.,0.],times=[-4.,-3.,-2.,-1.],dt=1.)
    m=Model(fixture,'coefficient*u');assert m.predict([row],[2.])[0]==1.
    e.write(HERE/'INTERFACE_CHECK.json',dict(passed=True,scope='Complete named parameter declaration and raw response binding; no discovery evidence'))
    e.write(HERE/'visible/evidence.json',e.read(PARENT/'visible/evidence.json'))
    rng=np.random.default_rng(3104301)
    designs=[dict(u=float(rng.uniform(-1.1,1.1)),h=float(rng.uniform(0,2.5)),history=rng.uniform(-1,1,4).tolist(),times=[-4.,-3.,-2.,-1.],dt=1.) for _ in range(160)]
    e.write(HERE/'evaluator_only/hidden.json',e.evaluator.acquire(designs,3104302,1))
    files=['continue_run.py','PROTOCOL.md','full_schema.json','INTERFACE_CHECK.json','visible/evidence.json','evaluator_only/hidden.json',
           '../run.py','../model_language.py','../evaluator.py','../SUMMARY.json','../FROZEN.json']
    files += ['../'+str(p.relative_to(PARENT)) for p in (PARENT/'calls').rglob('*') if p.is_file()]
    files += ['../'+str(p.relative_to(PARENT)) for p in (PARENT/'steps').glob('*.json')]
    e.write(HERE/'FROZEN.json',dict(time=e.now(),files={p:e.sha(HERE/p) for p in files},
       prior_stage_files=e.read(PARENT/'FROZEN.json')['prior_stage_files'],sterile_instructions_sha256=e.sha(e.STERILE/'AGENTS.md'),
       total_call_cap=6,already_used=4,remaining=2,requested_model='gpt-6-luna',effort='low'))
    print('Amendment frozen: 4 used, 2 remaining; original outputs retained.')


def run():
    e.ROOT=HERE;e.verify()
    visible=e.read(HERE/'visible/evidence.json');train=visible['fit'];dev=list(visible['dev'])
    prior=[]
    for p in sorted((PARENT/'calls').glob('*/reply.json')):
        idx=int(p.parent.name[:2]);stage=p.parent.name[3:]
        toolfile=PARENT/'steps'/f'{idx:02d}_{"build_audit" if stage=="build" else "fit"}.json'
        prior.append(dict(call=idx,stage=stage,proposal=e.read(p),tool_feedback=e.read(toolfile)))
    candidates=[];fresh=[]
    for index in [5,6]:
        bundle=dict(stage='complete named model and scientific revision',
          task='Explain the raw observations by discovering a useful variable definition and/or replacement response law. Use concrete observed failures to choose revisions. No new variable is mandatory; complete rewriting is permitted.',
          evidence=dict(metadata=visible['metadata'],fit=train,dev=dev),language=e.LANGUAGE,
          interface_correction='The former two-step interface froze an incomplete parameter list before response composition. Submit all shared coefficients, quantity definitions and the complete expression together. Every name used in the expression must be declared. All parameters are fitted on original fit only. This change supplies no scientific terms or values.',
          instruction='Submit exactly ONE complete specification matching the schema. Parameter dimensions must make every operation valid and the final output a scalar raw response [0,1]. Choose up to four previously unobserved executable conditions. evidence_refs must contain actual row_id strings; rationale and scientific_change explain your reasoning. Use the numerical and prospective feedback if available to revise the model.',
          budget=dict(call_index=index,total_call_cap=6,remaining_after_this=6-index,parameter_cap=8,actual_residual_call_cap=1600,rmse_threshold=.06),
          prior_steps=prior)
        reply=e.infer(index,'full',bundle)
        scaffold={k:reply[k] for k in e.schemas()['build']['properties']}
        result=e.cached(HERE/'steps'/f'{index:02d}_fit.json',lambda:fit(scaffold,reply['expression'],train,dev))
        try: capacity=capacity_audit(scaffold,dev,visible['metadata'])
        except Exception as exc:capacity=dict(error=str(exc))
        # Entire candidate already exists; no generation-prevention claim.
        cid=f'C{index}'
        c=dict(id=cid,scaffold=scaffold,expression=reply['expression'],annotation=reply,result=result,
               capacity_screen_after_generation=capacity,dev_row_ids=[r['row_id'] for r in dev])
        e.cached(HERE/'candidates'/(cid+'.json'),lambda:c);candidates.append(c)
        feedback=dict(call=index,proposal=reply,tool_feedback=result)
        if index==5 and result['status']=='executed':
            fresh=e.acquire_for(c,train+dev,1);dev+=fresh
            feedback['prospective_experiment']=e.read(HERE/'experiments/batch_1/OBSERVATIONS.json')
        prior.append(feedback)
        print(json.dumps(dict(call=index,status=result['status'],fit_rmse=result.get('fit_rmse'),dev_rmse=result.get('dev_rmse'),fresh_rows=len(fresh))),flush=True)
    executed=[c for c in candidates if c['result']['status']=='executed'];common=[]
    for c in executed:
        try:
            score=rmse(Model(c['scaffold'],c['expression']).predict(dev,c['result']['values']),dev)
            common.append(dict(id=c['id'],dev_rmse=score,converged=c['result']['optimizer_converged']))
        except Exception as exc:common.append(dict(id=c['id'],dev_rmse=None,converged=False,error=str(exc)))
    eligible=[r for r in common if r['dev_rmse'] is not None and r['dev_rmse']<=.06 and r['converged']]
    # If no model qualifies, still freeze the lowest-dev runnable candidate for
    # diagnosis; eligibility stays false and cannot become acceptance via hidden.
    ranked=[r for r in common if r['dev_rmse'] is not None]
    selected=min(eligible or ranked,key=lambda r:r['dev_rmse'])['id'] if ranked else None
    e.cached(HERE/'SELECTION_FREEZE.json',lambda:dict(time=e.now(),selected=selected,dev_eligible=bool(eligible),common_development=common,
       development_row_ids=[r['row_id'] for r in dev],candidate_hashes={c['id']:e.sha(HERE/'candidates'/(c['id']+'.json')) for c in candidates},hidden_read=False))
    selected_candidate=next((c for c in candidates if c['id']==selected),None)
    prospective=None
    if selected_candidate:
        e.acquire_for(selected_candidate,train+dev,2)
        prospective=e.read(HERE/'experiments/batch_2/OBSERVATIONS.json')
    hidden=e.read(HERE/'evaluator_only/hidden.json');independent=[]
    for c in executed:
        try:
            score=rmse(Model(c['scaffold'],c['expression']).predict(hidden,c['result']['values']),hidden)
            independent.append(dict(id=c['id'],hidden_rmse=score,selected=c['id']==selected))
        except Exception as exc:independent.append(dict(id=c['id'],error=str(exc)))
    selected_result=next((r for r in independent if r['id']==selected),{})
    accepted=bool(eligible and selected_result.get('hidden_rmse',1e9)<=.06 and prospective and prospective.get('rmse') is not None and prospective['rmse']<=.06)
    e.cached(HERE/'INDEPENDENT_RESULTS.json',lambda:dict(time=e.now(),results=independent,selected=selected,prospective_rmse=prospective.get('rmse') if prospective else None,
       fully_accepted=accepted,selection_sha256=e.sha(HERE/'SELECTION_FREEZE.json'),hidden_sha256=e.sha(HERE/'evaluator_only/hidden.json')))
    e.verify()
    total_calls=len(list((PARENT/'calls').glob('*/reply.json')))+len(list((HERE/'calls').glob('*/reply.json')))
    assert total_calls<=6
    summary=dict(time=e.now(),total_research_calls=total_calls,original_recovery_calls=4,amendment_calls=2,
       original_failed_complete_proposals=2,amendment_proposals=len(candidates),executable_proposals=len(executed),
       selected=selected,common_development=common,independent=independent,final_prospective_rmse=prospective.get('rmse') if prospective else None,
       fully_accepted=accepted,residual_calls=sum(c['result'].get('residual_calls',0) for c in candidates),
       numerical_feedback_before_call6=bool(candidates[0]['result']['status']=='executed'),
       expressions=[dict(id=c['id'],expression=c['expression'],quantities=c['scaffold']['quantities']) for c in candidates],
       original_stage_and_recovery_preserved=True,generation_control_benefit_established=False,
       scope='Development recovery and prospective prediction; generic known family rediscovery can be useful without establishing world novelty')
    e.cached(HERE/'SUMMARY.json',lambda:summary)
    print(json.dumps(summary,ensure_ascii=False),flush=True)


if __name__=='__main__':
    if sys.argv[1]=='prepare':prepare()
    elif sys.argv[1]=='run':run()
