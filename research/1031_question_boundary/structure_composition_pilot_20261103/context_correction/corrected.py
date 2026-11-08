"""Conditional context adapter; preserves scientific partitions and frozen history."""
import copy
from pathlib import Path
import re
import sys
import numpy as np

ROOT=Path(__file__).resolve().parent;PARENT=ROOT.parent
sys.path.insert(0,str(PARENT))
import pilot as p
import structure_tools as st
from model_language import RAW
e=p.e;p.ROOT=ROOT;e.ROOT=ROOT;e.STERILE=Path('/private/tmp/idea-composition-context-20261103-inference')
ORIGINAL_CERTIFICATE=st.additive_certificate


def normalize(proposal,index,rows,fixed_scope):
    left=proposal['left'];right=proposal['right']
    if not left or not right or len(set(left+right))!=len(left+right) or not set(left+right)<=set(RAW):
        raise ValueError('Variable groups must be nonempty, disjoint, unique raw input names')
    omitted=[n for n in RAW if n not in left+right]
    for name in omitted:
        vals={st.key(r,[name]) for r in rows}
        if len(vals)!=1 or name not in fixed_scope or st.key(rows[0],[name])!=st.key(fixed_scope,[name]):
            raise ValueError('Omitted input is not fixed in both observed data and declared intervention scope: '+name)
    return dict(id='P'+str(index),left=list(left),right=list(right),context=omitted,
                reason=proposal['reason'],evidence_refs=proposal['evidence_refs'],original_proposal=proposal)


def context_partition(proposal):
    left=proposal['left'];right=proposal['right'];context=proposal.get('context',[])
    if not left or not right or len(set(left+right+context))!=len(left+right+context) or set(left+right+context)!=set(RAW):
        raise ValueError('Partition plus fixed context must cover all raw inputs without overlap')
    return left+context,right+context


st.partition=context_partition


def context_certificate(rows,proposal,premises,threshold=.06):
    result=ORIGINAL_CERTIFICATE(rows,proposal,premises,threshold)
    fixed_scope=e.read(ROOT/'FIXED_CONTEXT.json') if (ROOT/'FIXED_CONTEXT.json').exists() else dict(times=[-4.,-3.,-2.,-1.],dt=1.)
    ok=all(name in fixed_scope and all(st.key(r,[name])==st.key(fixed_scope,[name]) for r in rows) for name in proposal.get('context',[]))
    result['context_scope_valid']=ok;result['fixed_context']={n:fixed_scope[n] for n in proposal.get('context',[]) if n in fixed_scope}
    if not ok:result['hard_excluded']=False
    return result


p.additive_certificate=context_certificate


def checks():
    from checks import run
    result=run()
    def check(name,value):assert value,name;result.append(dict(name=name,passed=True))
    rows=e.read(PARENT/'visible/evidence.json')['dev'];proposals=e.read(PARENT/'calls/01_constraints/reply.json')['partitions']
    scope=dict(times=[-4.,-3.,-2.,-1.],dt=1.)
    normalized=[normalize(q,i+1,rows,scope) for i,q in enumerate(proposals)]
    check('original varying-input grouping unchanged',all(q['left']==old['left'] and q['right']==old['right'] for q,old in zip(normalized,proposals)))
    check('only provably fixed missing inputs become context',all(set(q['context'])=={'times','dt'} for q in normalized))
    check('identifier length cannot discard scientific proposal',len(normalized)==3 and normalized[1]['id']=='P2')
    bad=dict(proposals[0],left=['u'],right=['history'])
    try:normalize(bad,1,rows,scope);ok=False
    except ValueError:ok=True
    check('omitted varying input still rejected',ok)
    varied=copy.deepcopy(rows);varied[0]['times'][0]-=.1
    try:normalize(proposals[0],1,varied,scope);ok=False
    except ValueError:ok=True
    check('changing background is not silently treated as fixed',ok)
    premise=e.read(PARENT/'visible/evidence.json')['metadata']
    c=context_certificate(rows,normalized[0],premise)
    check('context adapter preserves known empirical bound',abs(c['minimum_rmse']-.10536671677205334)<1e-12)
    check('background-scope change withdraws hard restriction',not context_certificate(varied,normalized[0],premise)['hard_excluded'])
    return result


def verify():
    p.verify_history()
    for name,h in e.read(ROOT/'FROZEN.json')['original_pilot_hashes'].items():assert e.sha(PARENT/name)==h,name


def prepare():
    # Seal the first attempt before deriving any corrected controller artifacts.
    if not (PARENT/'ATTEMPT1_SEAL.json').exists():
        e.write(PARENT/'ATTEMPT1_SEAL.json',dict(time=e.now(),files={str(f.relative_to(PARENT)):e.sha(f) for f in PARENT.rglob('*') if f.is_file() and ROOT not in f.parents and '__pycache__' not in f.parts and f.name!='ATTEMPT1_SEAL.json'}))
    e.write(ROOT/'FIXED_CONTEXT.json',dict(times=[-4.,-3.,-2.,-1.],dt=1.))
    e.write(ROOT/'IMPLEMENTATION_CHECKS.json',checks())
    ev=e.read(PARENT/'visible/evidence.json');e.write(ROOT/'visible/evidence.json',ev)
    e.write(ROOT/'raw_proposals.json',e.read(PARENT/'calls/01_constraints/reply.json'))
    e.write(ROOT/'previously_observed_conditions.json',[{k:r[k] for k in ['u','h','history','times','dt']} for r in e.read(PARENT/'NEW_OBSERVATIONS.json')['rows']])
    rng=np.random.default_rng(31103011)
    def design():return dict(u=float(rng.uniform(-1.1,1.1)),h=float(rng.uniform(0,2.5)),history=rng.uniform(-1,1,4).tolist(),times=[-4.,-3.,-2.,-1.],dt=1.)
    hidden=[design() for _ in range(160)];fixed=[dict(design(),source='fixed_confirmation',design_id='fixed_'+str(i)) for i in range(4)]
    e.write(ROOT/'evaluator_only/hidden.json',e.evaluator.acquire(hidden,31103012,1));e.write(ROOT/'confirmation_designs.json',fixed)
    e.STERILE.mkdir(exist_ok=False);e.write(e.STERILE/'AGENTS.md','Use only supplied serialized evidence. No tools, files, memory, network, or delegation. Answer directly in the requested JSON.\n')
    files=['corrected.py','PROTOCOL.md','FIXED_CONTEXT.json','IMPLEMENTATION_CHECKS.json','visible/evidence.json','raw_proposals.json',
           'previously_observed_conditions.json','evaluator_only/hidden.json','confirmation_designs.json','../pilot.py','../structure_tools.py','../model_language.py','../checks.py',
           '../../structure_search_recovery_20261103/run.py','../../structure_search_recovery_20261103/evaluator.py','../../structure_search_recovery_20261103/RESULTS_SEAL.json']
    e.write(ROOT/'FROZEN.json',dict(time=e.now(),files={name:e.sha(ROOT/name) for name in files},
       original_pilot_hashes=e.read(PARENT/'ATTEMPT1_SEAL.json')['files'],prior_stage_files=e.read(p.PREVIOUS/'FROZEN.json')['prior_stage_files'],
       sterile_instructions_sha256=e.sha(e.STERILE/'AGENTS.md'),new_call_cap=4,total_turn_call_cap=9,model='gpt-6-luna',effort='low'))
    print('Context correction frozen; 19 checks; four additional calls, nine total.')


def shared(ev):
    raw=e.read(ROOT/'raw_proposals.json');scope=e.read(ROOT/'FIXED_CONTEXT.json')
    def calculate():
        valid=[];invalid=[]
        for i,q in enumerate(raw['partitions']):
            try:
                proposal=normalize(q,i+1,ev['fit']+ev['dev'],scope)
                cert=context_certificate(ev['dev'],proposal,ev['metadata']);cert['proposal']=proposal
                valid.append(cert)
            except Exception as exc:invalid.append(dict(proposal=q,error=str(exc)))
        return dict(time=e.now(),certificates=valid,invalid=invalid,source_proposals_sha256=e.sha(ROOT/'raw_proposals.json'))
    certs=e.cached(ROOT/'CONSTRAINT_CERTIFICATES.json',calculate)
    proposals=[c['proposal'] for c in certs['certificates']]
    compact=[{k:v for k,v in c.items() if k!='dual_residual'} for c in certs['certificates']]
    package=dict(original_proposals=raw,verified=compact,invalid=certs['invalid'],
       context_rule='Only inputs fixed in all observed records AND the declared experiment scope can be shared context. Varying-variable groups are unchanged.',exact_certificate_sha256=e.sha(ROOT/'CONSTRAINT_CERTIFICATES.json'))
    if not (ROOT/'GENERATION_FREEZE.json').exists():
        for arm in ['F','G']:
            control=st.allowed_operations(proposals,certs['certificates'],arm);e.write(ROOT/'controls'/(arm+'.json'),control)
            e.write(ROOT/(arm+'_plan_schema.json'),e.object_schema(dict(operation=dict(type='string',enum=control['allowed']),reason=e.S,evidence_refs=e.array(e.S))))
        e.write(ROOT/'SHARED_CONSTRAINT_PACKAGE.json',package)
        files=['CONSTRAINT_CERTIFICATES.json','SHARED_CONSTRAINT_PACKAGE.json','controls/F.json','controls/G.json','F_plan_schema.json','G_plan_schema.json']
        e.write(ROOT/'GENERATION_FREEZE.json',dict(time=e.now(),files={f:e.sha(ROOT/f) for f in files},complete_predictor_submitted=False))
    p.verify_generation();return proposals,package


def run():
    verify();ev=e.read(ROOT/'visible/evidence.json');proposals,package=shared(ev)
    plans={'F':p.plan('F',2,ev,package,proposals),'G':p.plan('G',3,ev,package,proposals)}
    candidates=[p.complete('F',4,ev,package,proposals,plans['F']),p.complete('G',5,ev,package,proposals,plans['G'])]
    # Preserve raw requests; filter old conditions into an explicit audit before
    # passing copies to the already frozen common acquisition implementation.
    old={e.design_key(r) for r in e.read(ROOT/'previously_observed_conditions.json')};filtered=copy.deepcopy(candidates);removed=[]
    for c in filtered:
        keep=[]
        for req in c['raw']['experiments']:
            d=dict(req,times=[-4.,-3.,-2.,-1.],dt=1.)
            if e.design_key(d) in old:removed.append(dict(arm=c['arm'],request=req,reason='Observed in first pilot attempt'))
            else:keep.append(req)
        c['raw']['experiments']=keep
    e.cached(ROOT/'REQUEST_DUPLICATE_AUDIT.json',lambda:removed)
    independent=p.select_and_test(filtered,ev);verify();p.verify_generation()
    usage={}
    for f in (ROOT/'calls').glob('*/completion_*.json'):
        item=e.read(f);assert not item['tool_violations']
        for k,v in item['usage'].items():usage[k]=usage.get(k,0)+v
    summary=dict(time=e.now(),new_calls=len(list((ROOT/'calls').glob('*/reply.json'))),original_calls=5,total_turn_calls=9,
       certificates=[{k:c[k] for k in ['id','left','right','fixed_context','minimum_rmse','hard_excluded']} for c in e.read(ROOT/'CONSTRAINT_CERTIFICATES.json')['certificates']],
       plans=plans,controls={a:e.read(ROOT/'controls'/(a+'.json')) for a in ['F','G']},
       candidates=[dict(arm=c['arm'],expression=c.get('expression'),operation=c['operation'],status=c['result']['status'],
                       class_violation=c.get('post_generation_certified_violation'),residual_calls=c['result'].get('residual_calls',0)) for c in candidates],
       independent=independent,usage=usage,scope='One valid development pair after separately recorded interface correction; no average advantage or open-discovery conclusion')
    e.cached(ROOT/'SUMMARY.json',lambda:summary);print(e.json.dumps(summary,ensure_ascii=False),flush=True)


if __name__=='__main__':
    if sys.argv[1]=='prepare':prepare()
    elif sys.argv[1]=='run':run()
