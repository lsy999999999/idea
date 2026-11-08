"""Four scientific decisions with experiment acquisition between revisions."""
import copy
import importlib.util
from pathlib import Path
import sys
import time
import numpy as np
from transport import ROOT,PREVIOUS,STERILE,now,read,sha,write,cached,verify,infer
from model_language import Model,rmse
from tools import complete_model,FeatureProgram,automatic_library
from experiment_tools import make_offers,validate_selection,predict,experiment_feedback,scoped_capacity

SIM_PATH=ROOT.parent/'structure_search_recovery_20261103/evaluator.py'
spec=importlib.util.spec_from_file_location('organizer_only',SIM_PATH)
simulator=importlib.util.module_from_spec(spec);spec.loader.exec_module(simulator)

def obj(p):return dict(type='object',properties=p,required=list(p),additionalProperties=False)
def arr(x,**kw):return dict(type='array',items=x,**kw)
S=dict(type='string');N=dict(type='number');IDENT=dict(type='string',pattern='^[A-Za-z][A-Za-z0-9_]*$')
PARAM=obj(dict(name=IDENT,lower=N,initial=N,upper=N))
QUANTITY=obj(dict(name=IDENT,expression=S,interpretation=S))
PROPOSAL=obj(dict(label=S,parameters=arr(PARAM,maxItems=2),quantities=arr(QUANTITY,maxItems=4),features=arr(S,minItems=1,maxItems=4),degree=dict(type='integer',enum=[1,2,3]),
    kernel_family_claim=dict(type='string',enum=['exponential','oscillatory','polynomial','other','none']),scientific_change=S,evidence_refs=arr(S),prospective_contrast=S,refutation_condition=S))
DESIGN=obj(dict(u=N,h=N,history=arr(N,minItems=4,maxItems=4)))
SCHEMAS=dict(propose=obj(dict(proposals=arr(PROPOSAL,minItems=1,maxItems=2),reason=S)),
    experiment=obj(dict(offer_ids=arr(S,maxItems=2),manual_pairs=arr(obj(dict(a=DESIGN,b=DESIGN)),maxItems=2),reason=S,expected_distinction=S,revision_if_refuted=S)),
    revise=obj(dict(proposals=arr(PROPOSAL,minItems=1,maxItems=2),experiment_interpretation=S)),
    select=obj(dict(candidate_id=S,reason=S,refuted_assumptions=arr(S),remaining_uncertainties=arr(S),evidence_refs=arr(S))))
LANGUAGE=dict(raw_inputs=dict(u='dimensionless current drive',h='waiting time, seconds',history='4 dimensionless drive intervals oldest first',times='interval end times [-4,-3,-2,-1] seconds',dt='interval duration 1 second'),
    operators=['+','-','*','/','**','sum','mean','exp','log','sqrt','abs','sin','cos','tanh','index [0]..[3] of history or times'],
    syntax='Every expression is ONE pure expression, no assignment or semicolons. No literal lists, ranges, slicing, loops or row-dependent parameters. Use raw times instead of writing a time vector. Define quantities sequentially. All parameter names referenced must occur in parameters. Finite lower<initial<upper. Do NOT declare automatic linear response coefficients; declare only nonlinear parameters actually used in features/quantities. Tool infers units and creates output coefficients.',
    completion='You choose 1..4 scalar features and polynomial degree1..3. The tool may form powers/products of only those features and fits at most8 total parameters, including at most2 nonlinear parameters. It does not invent omitted inputs or history transformations.',
    experiments='u [-1.1,1.1], h [0,2.5], each history entry [-1,1]; only these inputs and scalar response can be measured. No internal sensor. New conditions must differ from all supplied observations. Up to2 pairs,4 repeats per condition, frozen forecasts before acquisition.')

def prepare():
    for p,h in read(PREVIOUS/'FINAL_RESULTS_SEAL.json')['files'].items():assert sha(PREVIOUS/p)==h,p
    from checks import run
    write(ROOT/'IMPLEMENTATION_CHECKS.json',run())
    old=read(PREVIOUS/'amendment1/visible/evidence.json')
    write(ROOT/'visible/initial.json',old)
    c=read(PREVIOUS/'amendment1/SELECTION_FREEZE.json')['selected']['agent_tools']
    request={k:c['annotation'][k] for k in ['parameters','quantities','features','degree']}
    current={k:c[k] for k in ['scaffold','expression','values','train_rmse','dev_rmse','optimizer_converged']}
    current.update(id='C0',request=request,origin='Prior frozen agent-selected model; its failure is supplied task context')
    write(ROOT/'current_model.json',current)
    write(ROOT/'tool_only_request.json',automatic_library())
    rng=np.random.default_rng(41104002)
    def design():return dict(u=float(rng.uniform(-1.1,1.1)),h=float(rng.uniform(0,2.5)),history=rng.uniform(-1,1,4).tolist(),times=[-4.,-3.,-2.,-1.],dt=1.)
    write(ROOT/'evaluator_only/hidden.json',simulator.acquire([design() for _ in range(200)],41104003,1))
    write(ROOT/'confirmation_designs.json',[dict(design(),design_id='random_'+str(i)) for i in range(16)])
    for stage,schema in SCHEMAS.items():write(ROOT/(stage+'_schema.json'),schema)
    STERILE.mkdir(exist_ok=False)
    write(STERILE/'AGENTS.md','Inference-only task. Use only serialized observations and tool results. Do not read files or memory, use native tools, shell, network or delegation. The runner executes requested scientific tools and experiments. Return the requested JSON.\n')
    files=['run.py','transport.py','tools.py','model_language.py','experiment_tools.py','checks.py','PROTOCOL.md','IMPLEMENTATION_CHECKS.json','visible/initial.json','current_model.json','tool_only_request.json','evaluator_only/hidden.json','confirmation_designs.json','../structure_search_recovery_20261103/evaluator.py']+[stage+'_schema.json' for stage in SCHEMAS]
    write(ROOT/'FROZEN.json',dict(time=now(),files={p:sha(ROOT/p) for p in files},previous_files=read(PREVIOUS/'FINAL_RESULTS_SEAL.json')['files'],sterile_sha256=sha(STERILE/'AGENTS.md'),research_model='gpt-6-luna',effort='low',research_call_cap=4,scope='One repeated-mechanism development chain; experiment suggestions are tool-generated from candidate disagreement'))
    print(dict(prepared=True,checks=len(read(ROOT/'IMPLEMENTATION_CHECKS.json'))),flush=True)

def request_of(proposal):return {k:proposal[k] for k in ['parameters','quantities','features','degree']}

def semantic_check(proposal):
    expr=' '.join(proposal['features']+[q['expression'] for q in proposal['quantities']]);family=proposal['kernel_family_claim']
    if family=='exponential' and ('exp(' not in expr or any(f+'(' in expr for f in ['sin','cos','tanh'])):raise ValueError('Claimed exponential kernel conflicts with supplied operators; clarify scientific intent, do not auto-rewrite')
    if family=='oscillatory' and not any(f+'(' in expr for f in ['sin','cos']):raise ValueError('Claimed oscillatory kernel has no sin/cos operator')
    FeatureProgram(request_of(proposal))

def compact_candidate(c,ev,exp_rows):
    m=Model(c['scaffold'],c['expression']);d=dict(id=c['id'],request=c['request'],expression=c['expression'],quantities=c['scaffold']['quantities'],parameters=dict(zip([p['name'] for p in c['scaffold']['parameters']],c['values'])),
          current_dev_rmse=rmse(m.predict(ev['dev'],c['values']),ev['dev']))
    d['experiment_pair_rmse']={pid:rmse(m.predict([r for r in exp_rows if r['pair_id']==pid],c['values']),[r for r in exp_rows if r['pair_id']==pid]) for pid in sorted({r['pair_id'] for r in exp_rows})}
    if 'annotation' in c:d['scientific_proposal']=c['annotation']
    return d

def complete_proposals(reply,stage,ev,exp_rows,budget):
    records=[];selected=[]
    for i,proposal in enumerate(reply['proposals'],1):
        cid=('C' if stage=='initial' else 'R')+str(i)
        def execute():
            try:
                semantic_check(proposal);request=request_of(proposal)
                cap=scoped_capacity(request,ev['dev'],exp_rows,ev['metadata'])
                if not cap['completion_enabled']:return dict(status='representation_rejected_before_response_search',capacity=cap,candidates=[],budget_after=budget.copy())
                result,pool=complete_model(request,ev['fit'],ev['dev'],ev['metadata'],ROOT/'search_traces'/(cid+'.jsonl'),budget)
                return dict(status=result['status'],capacity=cap,result=result,candidates=pool,budget_after=budget.copy())
            except Exception as exc:return dict(status='invalid_proposal',error=str(exc),candidates=[],budget_after=budget.copy())
        path=ROOT/'completion'/(cid+'.json');result=cached(path,execute);budget.update(result['budget_after'])
        record=dict(id=cid,proposal=proposal,**result);records.append(record)
        if result['candidates']:
            best=min(result['candidates'],key=lambda c:(c['dev_rmse'],len(c['values']),c['expression']))
            selected.append(dict(best,id=cid,request=request_of(proposal),annotation=proposal,fit_rows_sha256=__import__('hashlib').sha256(__import__('json').dumps(ev['fit'],sort_keys=True).encode()).hexdigest()))
        print(dict(candidate=cid,status=result['status'],dev_rmse=selected[-1]['dev_rmse'] if selected and selected[-1]['id']==cid else None,budget=budget),flush=True)
    return records,selected

def baseline(stage,ev):
    def execute():
        budget=dict(residual_calls=0,linear_solves=0)
        result,pool=complete_model(read(ROOT/'tool_only_request.json'),ev['fit'],ev['dev'],ev['metadata'],ROOT/'search_traces'/('baseline_'+stage+'.jsonl'),budget)
        return dict(result=result,candidates=pool,budget=budget)
    return cached(ROOT/'baseline'/(stage+'.json'),execute)

def base_bundle(ev):return dict(evidence=ev,language=LANGUAGE,task='Discover a useful response representation from failed o=f(u,h), extending or replacing the function as supported by evidence. The current model is a previous failed agent proposal, not a required structure. Use concrete quantities and executable experiments.',acceptance='Raw response RMSE<=0.06 on dev, fresh hidden observations, random confirmation and each acquired intervention pair. Final independent targets cannot be used for revision.')

def acquire(reply,offers,candidates,ev):
    selection=cached(ROOT/'experiment/VALIDATION.json',lambda:validate_selection(reply,offers,candidates,ev['fit']+ev['dev']))
    designs=[]
    for item in selection['selected']:
        for condition,d in enumerate(item['designs']):designs.append(dict(d,pair_id=item['id'],condition=condition,design_id=item['id']+'_'+str(condition)))
    forecasts={c['id']:predict(c,designs).tolist() if designs else [] for c in candidates}
    cached(ROOT/'experiment/PREDICTION_FREEZE.json',lambda:dict(time=now(),selected_pairs=selection['selected'],designs=designs,predictions=forecasts,candidates=candidates,selected_by='research model after tool-generated offers; manual requests separately labelled',raw_choice_sha256=sha(ROOT/'calls/02_experiment/reply.json')))
    def observe():
        rows=simulator.acquire(designs,41104004,4)
        return dict(time=now(),rows=[dict(r,row_id='active_'+str(i)) for i,r in enumerate(rows)],prediction_sha256=sha(ROOT/'experiment/PREDICTION_FREEZE.json'))
    observations=cached(ROOT/'experiment/OBSERVATIONS.json',observe)
    feedback=cached(ROOT/'experiment/FEEDBACK.json',lambda:experiment_feedback(selection['selected'],observations['rows'],candidates,ev['metadata']))
    return selection,observations['rows'],feedback

def final_test(selected,all_candidates,ev,exp_rows):
    tool_pre=baseline('initial',read(ROOT/'visible/initial.json'))
    tool_post=baseline('augmented',ev)
    arms={'agent_selected':selected}
    for label,data in [('tool_initial',tool_pre),('tool_same_data',tool_post)]:
        c=data['result'].get('best')
        arms[label]=dict(c,id=label,request=read(ROOT/'tool_only_request.json')) if c else None
    backup=min(all_candidates,key=lambda c:(rmse(predict(c,ev['dev']),ev['dev']),len(c['values']),c['id']))
    arms['dev_rule_backup']=backup
    cached(ROOT/'FINAL_SELECTION_FREEZE.json',lambda:dict(time=now(),arms=arms,hidden_read=False,expanded_dev_row_ids=[r['row_id'] for r in ev['dev']]))
    designs=read(ROOT/'confirmation_designs.json')
    forecasts={a:predict(c,designs).tolist() if c else None for a,c in arms.items()}
    cached(ROOT/'CONFIRMATION_PREDICTIONS.json',lambda:dict(time=now(),designs=designs,predictions=forecasts,selection_sha256=sha(ROOT/'FINAL_SELECTION_FREEZE.json')))
    confirmation=cached(ROOT/'CONFIRMATION_OBSERVATIONS.json',lambda:dict(time=now(),rows=simulator.acquire(designs,41104005,4),forecast_sha256=sha(ROOT/'CONFIRMATION_PREDICTIONS.json')))['rows']
    hidden=read(ROOT/'evaluator_only/hidden.json');original=read(ROOT/'visible/initial.json');results=[]
    for arm,c in arms.items():
        r=dict(arm=arm,accepted=False)
        if c:
            r.update(candidate_id=c['id'],original_dev_rmse=rmse(predict(c,original['dev']),original['dev']),expanded_dev_rmse=rmse(predict(c,ev['dev']),ev['dev']),hidden_rmse=rmse(predict(c,hidden),hidden),random_confirmation_rmse=rmse(predict(c,confirmation),confirmation))
            r['active_pairs_rmse']={pid:rmse(predict(c,[x for x in exp_rows if x['pair_id']==pid]),[x for x in exp_rows if x['pair_id']==pid]) for pid in sorted({x['pair_id'] for x in exp_rows})}
            r['accepted']=all(v<=.06 for k,v in r.items() if k.endswith('_rmse') and isinstance(v,float)) and all(v<=.06 for v in r['active_pairs_rmse'].values())
        results.append(r)
    return cached(ROOT/'INDEPENDENT_RESULTS.json',lambda:dict(time=now(),results=results,hidden_rows=len(hidden),random_confirmation_rows=len(confirmation),active_conditions=len({r['design_id'] for r in exp_rows})))

def run():
    verify();ev=read(ROOT/'visible/initial.json');budget=dict(residual_calls=0,linear_solves=0);candidates=[read(ROOT/'current_model.json')]
    bundle=base_bundle(ev);bundle.update(current_model=compact_candidate(candidates[0],ev,[]),instruction='Propose at most TWO competing replacements. You may change the complete representation and function class. Ground differences in specific observations, and describe a future contrast. Submit complete feature requests, not response coefficients. An unmeasured latent symbol is insufficient. All referenced nonlinear parameters must be declared. Do not repeat known observations as new experiments.')
    first=infer(1,'propose',bundle);records,models=complete_proposals(first,'initial',ev,[],budget);candidates+=models
    cached(ROOT/'INITIAL_MODELS.json',lambda:dict(candidates=candidates,completion_records=records,budget=budget.copy()))
    offers=cached(ROOT/'EXPERIMENT_OFFERS.json',lambda:make_offers(candidates,ev['fit']+ev['dev']))
    bundle=base_bundle(ev);bundle.update(candidates=[compact_candidate(c,ev,[]) for c in candidates],experiment_offers=offers,
      instruction='Choose at most TWO experiment PAIRS total, by offer_ids or manual_pairs. Empty manual_pairs is fine. Tool suggestions were generated by frozen model disagreement while changing one controllable coordinate; their predictions are actual executable model predictions. Choose tests that distinguish representations, and state what you would revise. You may instead submit your own two novel controlled conditions as one manual pair. All chosen conditions must be new. Predictions are frozen before new observations. Up to4 conditions,4 repeats each.')
    choice=infer(2,'experiment',bundle);selection,exp_rows,feedback=acquire(choice,offers,candidates,ev)
    augmented=copy.deepcopy(ev);augmented['fit']+=[r for r in exp_rows if r['repeat']<2];augmented['dev']+=[r for r in exp_rows if r['repeat']>=2]
    cached(ROOT/'visible/augmented.json',lambda:augmented)
    bundle=base_bundle(augmented);bundle.update(active_observations=exp_rows,frozen_prediction_results=feedback,experiment_choice=choice,
      candidates=[compact_candidate(c,augmented,exp_rows) for c in candidates],
      instruction='Use the NEW experiment results to propose up to TWO revised representations. Explain which empirical distinction each revision preserves and what the observations actually refute. A fixed fitted formula failing does not refute an entire feature class unless a scoped collision certificate proves it. Each proposal is checked against old evidence AND each active pair before response search; provably insufficient representations cannot be completed. Preserve all already supported distinctions. All parameters must be declared and the claimed kernel family must agree with the mathematical operators.')
    revision=infer(3,'revise',bundle);recs,models=complete_proposals(revision,'revised',augmented,exp_rows,budget);candidates+=models
    cached(ROOT/'REVISED_MODELS.json',lambda:dict(candidates=candidates,completion_records=recs,budget=budget.copy()))
    bundle=base_bundle(augmented);bundle.update(active_experiment_results=feedback,candidates=[compact_candidate(c,augmented,exp_rows) for c in candidates],invalid_revisions=[dict(id=r['id'],status=r['status'],error=r.get('error'),capacity=r.get('capacity')) for r in recs if not r['candidates']],
      instruction='Select ONE existing candidate_id; do not change any formula or fitted parameter. Explain whether any model is adequate and which assumptions were refuted versus not resolved. Selecting the best available model does not make it accepted. Cite experiment ids or row ids. Final independent tests happen after this choice.')
    final=infer(4,'select',bundle);selected=next((c for c in candidates if c['id']==final['candidate_id']),None)
    cached(ROOT/'AGENT_SELECTION.json',lambda:dict(time=now(),raw=final,valid=selected is not None,selected=selected))
    results=final_test(selected,candidates,augmented,exp_rows);verify();usage={}
    for p in (ROOT/'calls').glob('*/completion_*.json'):
        for k,v in read(p)['usage'].items():usage[k]=usage.get(k,0)+v
    summary=dict(time=now(),research_calls=4,usage=usage,agent_budget=budget,initial_model_ids=[c['id'] for c in read(ROOT/'INITIAL_MODELS.json')['candidates']],revised_model_ids=[c['id'] for c in models],
      experiment_offers=len(offers),selected_pairs=len(selection['selected']),manual_selected_pairs=sum(p['varied_coordinate']=='agent-specified' for p in selection['selected']),rejected_requests=selection['rejected'],
      final_agent_choice=final['candidate_id'],active_feedback_delivered=bool(exp_rows),active_process_completed=bool(exp_rows) and bool(models) and selected is not None,independent=results)
    cached(ROOT/'SUMMARY.json',lambda:summary);print(summary,flush=True)

if __name__=='__main__':
    if sys.argv[1]=='prepare':prepare()
    elif sys.argv[1]=='run':run()
