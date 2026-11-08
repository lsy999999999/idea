"""Independent post-run checks; no researcher calls or candidate repair."""
import ast
import json
from pathlib import Path
import sys
import numpy as np
import sympy as sp
import pilot as p
from model_language import Model,RAW,parse,rmse
from structure_tools import key

ROOT=Path(__file__).resolve().parent;BR=ROOT/'context_correction';e=p.e


def certificate_check(c,rows):
    a=list(dict.fromkeys(key(r,c['left']) for r in rows));b=list(dict.fromkeys(key(r,c['right']) for r in rows))
    X=sp.zeros(len(rows),len(a)+len(b))
    for i,r in enumerate(rows):X[i,a.index(key(r,c['left']))]=1;X[i,len(a)+b.index(key(r,c['right']))]=1
    y=sp.Matrix([sp.Rational(str(r['o'])) for r in rows]);v=sp.Matrix([sp.Rational(x) for x in c['dual_residual']])
    assert X.T*v==sp.zeros(X.cols,1)
    assert X.row_join(y-v).rank()==X.rank()
    assert str((v.T*v)[0])==c['exact_sse']
    assert bool((v.T*v)[0]>sp.Rational('0.06')**2*len(rows))==c['exceeds_threshold']
    return dict(id=c['id'],exact_projection_and_dual_verified=True,minimum_rmse=c['minimum_rmse'],hard_excluded=c['hard_excluded'])


def audit_arm_pair(root):
    inputs={name:e.read(root/'calls'/name/'input.json') for name in ['02_F_plan','03_G_plan','04_F_full','05_G_full']}
    for k in ['evidence','constraint_package','language','resource_limits','scientific_goal']:
        assert inputs['02_F_plan'][k]==inputs['03_G_plan'][k]
        assert inputs['04_F_full'][k]==inputs['05_G_full'][k]
    for arm,index in [('F',2),('G',3)]:
        control=e.read(root/'controls'/(arm+'.json'));schema=e.read(root/(arm+'_plan_schema.json'))
        assert schema['properties']['operation']['enum']==control['allowed']
        chosen=e.read(root/'calls'/f'{index:02d}_{arm}_plan'/'reply.json')['operation']
        assert chosen in control['allowed']
        assert e.read(root/'GENERATION_FREEZE.json')['time']<e.read(root/'calls'/f'{index:02d}_{arm}_plan'/'SEALED.json')['time']
    pred=e.read(root/'PREDICTION_FREEZE.json');obs=e.read(root/'NEW_OBSERVATIONS.json');sel=e.read(root/'SELECTION_FREEZE.json')
    assert sel['time']<=pred['time']<=obs['time']
    assert obs['prediction_sha256']==e.sha(root/'PREDICTION_FREEZE.json')
    assert pred['selection_sha256']==e.sha(root/'SELECTION_FREEZE.json')
    for f in pred['forecasts']:
        c=e.read(root/'candidates'/(f['arm']+'.json'))
        if f['predictions'] is None:continue
        m=Model(c['scaffold'],c['expression']);values=c['result']['values']
        assert np.allclose(m.predict(pred['designs'],values),f['predictions'])
        result=next(r for r in e.read(root/'INDEPENDENT_RESULTS.json')['results'] if r['arm']==f['arm'])
        dev=inputs['04_F_full']['evidence']['dev'];hidden=e.read(root/'evaluator_only/hidden.json')
        assert abs(rmse(m.predict(dev,values),dev)-result['dev_rmse'])<1e-12
        assert abs(rmse(m.predict(hidden,values),hidden)-result['hidden_rmse'])<1e-12
        assert abs(rmse(m.predict(obs['rows'],values),obs['rows'])-result['all_prospective_rmse'])<1e-12
        assert c['result']['residual_calls']<=1600 and all(x['calls']<=400 for x in c['result']['attempts'])
    return dict(shared_scientific_input_identical=True,actual_schema_enums_match_controls=True,
                operation_schemas_frozen_before_plans=True,predictions_and_selection_before_observation=True,
                metrics_and_parameter_binding_independently_recomputed=True,fit_budget_respected=True)


def raw_dependencies(model,tree):
    deps={n:{n} for n in RAW};deps.update({x['name']:set() for x in model.parameters})
    def dep(t):
        out=set()
        for n in ast.walk(t):
            if isinstance(n,ast.Name):out|=deps.get(n.id,set())
        return out
    for name,t in model.qtrees:deps[name]=dep(t)
    return dep(tree)


def main():
    from context_correction import corrected
    corrected.verify()
    rows=e.read(BR/'visible/evidence.json')['dev']
    certs=e.read(BR/'CONSTRAINT_CERTIFICATES.json')['certificates']
    certchecks=[certificate_check(c,rows) for c in certs]
    pairchecks={root.name:audit_arm_pair(root) for root in [ROOT,BR]}
    # Diagnose G's raw branch failure without changing it or assigning a score.
    g=e.read(BR/'candidates/G.json');raw=g['raw'];scaffold={k:raw[k] for k in ['parameters','quantities','exposed_inputs']}
    model=Model(scaffold,raw['left_expression']);partition=next(c for c in certs if c['id']=='P3')
    leftdeps=raw_dependencies(model,model.tree)
    missing=sorted(leftdeps-set(partition['left']))
    assert missing==['u']
    righttree,typed=parse(raw['right_expression'],model.final_env)
    gdiagnosis=dict(original_error=g['result']['error'],left_actual_dependencies=sorted(leftdeps),left_allowed=partition['left'],
       forbidden_left_inputs=missing,right_expression=raw['right_expression'],right_inferred_dimension=list(map(str,typed[1])),
       right_scalar_zero_is_dimensionless_in_current_compiler=True,
       scope='Two independent issues. Even treating literal zero as unit-polymorphic would not repair the forbidden u dependency. No expression moved or repaired; no fit/acceptance assigned.')
    # Original F's alleged lag-specific weights reduce to one scalar times sum(H).
    f=e.read(ROOT/'candidates/F.json');fm=Model(f['scaffold'],f['expression']);vals=f['result']['values']
    probe=dict(u=.4,h=.7,history=[1.,0.,0.,0.],times=[-4.,-3.,-2.,-1.],dt=1.)
    reversed_probe=dict(probe,history=[0.,0.,0.,1.])
    delta=float(abs(np.diff(fm.predict([probe,reversed_probe],vals))[0]));assert delta<1e-12
    usage={};calls=[]
    for root in [ROOT,BR]:
        for q in (root/'calls').glob('*/completion_*.json'):
            d=e.read(q);assert d['returncode']==0 and not d['tool_violations'];calls.append(str(q.relative_to(ROOT)))
            for k,v in d['usage'].items():usage[k]=usage.get(k,0)+v
    assert len(calls)==9
    result=dict(time=e.now(),certificate_checks=certchecks,pair_checks=pairchecks,G_failure_diagnosis=gdiagnosis,
       original_F_order_contrast=delta,original_F_semantic_issue='All four scalar lag weights are summed before multiplying the history vector, so the program is invariant to history order despite a lag-specific narrative.',
       calls=9,usage=usage,original_history_seals_verified=True,
       scope='Organizer audit of frozen predictions, exact class certificates and construction failures. No new scientific candidate or model calls.')
    e.write(ROOT/'POSTRUN_AUDIT.json',result)
    print(json.dumps(dict(calls=9,usage=usage,G_branch_violation=missing,exact_certificates_verified=len(certchecks),paired_input_checks=pairchecks),ensure_ascii=False))


if __name__=='__main__':main()
