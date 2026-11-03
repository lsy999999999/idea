"""Organizer post-run audit: no model calls, refits or truth-based candidate repair."""
import ast
import json
from pathlib import Path
import numpy as np
import run as e
from model_language import Model, RAW, rmse

ROOT=Path(__file__).resolve().parent
BR=ROOT/'amendment1'


def additive_bound(rows, left, right):
    def key(row, names):
        return tuple(tuple(row[n]) if isinstance(row[n],list) else row[n] for n in names)
    ka=[key(r,left) for r in rows];kb=[key(r,right) for r in rows]
    a=list(dict.fromkeys(ka));b=list(dict.fromkeys(kb))
    X=np.zeros((len(rows),len(a)+len(b)))
    for i in range(len(rows)):X[i,a.index(ka[i])]=1;X[i,len(a)+b.index(kb[i])]=1
    y=np.array([r['o'] for r in rows]);beta=np.linalg.lstsq(X,y,rcond=None)[0];res=X@beta-y
    return dict(rows=len(rows),class_='A('+','.join(left)+') + B('+','.join(right)+')',
                left_levels=len(a),right_levels=len(b),rank=int(np.linalg.matrix_rank(X)),
                minimum_possible_rmse=float(np.sqrt(np.mean(res**2))),sse=float(res@res),
                normal_equation_max_abs=float(np.max(np.abs(X.T@res))),
                proof='On this finite set, allow an independent unrestricted value for A at each unique left input and B at each unique right input. This contains every shared deterministic additive model on the set. Global linear least squares therefore gives the exact class minimum empirical RMSE, irrespective of nonlinear function forms or parameter fitting.')


def additive_membership(model,left,right):
    deps={n:{n} for n in RAW};deps.update({p['name']:set() for p in model.parameters})
    def dependencies(tree):
        result=set()
        for n in ast.walk(tree):
            if isinstance(n,ast.Name):result|=deps.get(n.id,set())
        return result
    for name,tree in model.qtrees:deps[name]=dependencies(tree)
    def terms(t):
        if isinstance(t,ast.BinOp) and isinstance(t.op,(ast.Add,ast.Sub)):
            return terms(t.left)+terms(t.right)
        return [t]
    classified=[]
    for term in terms(model.tree):
        used=dependencies(term)
        group='left' if used<=set(left) else 'right' if used<=set(right) else 'unknown_cross_dependence'
        classified.append(dict(expression=ast.unparse(term),raw_dependencies=sorted(used),group=group))
    return dict(certified_additive=all(t['group']!='unknown_cross_dependence' for t in classified),terms=classified,
                scope='Sufficient syntactic dependency certificate; unknown expressions are never declared additive merely because analysis fails')


def main():
    e.verify()
    evidence=e.read(BR/'visible/evidence.json');fresh=e.read(BR/'experiments/batch_1/OBSERVATIONS.json')['rows']
    dev=evidence['dev']+fresh;left=['u','h'];right=['history','times','dt']
    memberships=[]
    for p in sorted((BR/'candidates').glob('*.json')):
        c=e.read(p);m=Model(c['scaffold'],c['expression'])
        membership=additive_membership(m,left,right)
        memberships.append(dict(id=c['id'],**membership))
    # Independent analytic certificate from the 24 original diagnostic records.
    old=evidence['dev'][:24]
    groups=[[r['o'] for r in old if r['h']==h and r['history'][0]==s] for h in [.3,1.2] for s in [1,-1]]
    assert all(len(g)==6 for g in groups)
    means=[float(np.mean(g)) for g in groups];contrast=means[0]-means[1]-means[2]+means[3]
    analytic_sse=6*contrast**2/4
    analytic=dict(means=means,group_n=6,difference_in_differences=contrast,
        min_sse_from_group_means=analytic_sse,rmse_lower_bound_on_80_rows=float(np.sqrt(analytic_sse/len(dev))),
        proof='For additive predictions, the signed four-group contrast is zero. Cauchy-Schwarz gives sum of four squared mean residuals >= observed contrast squared/4. Six repetitions per group imply SSE >= 6*contrast^2/4, before adding within-group noise or other records.')
    # Counterchecks for the structural tool, independent of simulator equation.
    add=additive_bound(dev,left,right);assert add['minimum_possible_rmse']>=analytic['rmse_lower_bound_on_80_rows']-.0000001
    assert add['normal_equation_max_abs']<1e-10
    c=e.read(BR/'candidates/C5.json');bad=Model(c['scaffold'],'a+b*u+c*h+d*memory*h/tau')
    assert not additive_membership(bad,left,right)['certified_additive']
    measurements=[]
    for name in ['batch_1','batch_2']:
        pred=e.read(BR/'experiments'/name/'PREDICTION_FREEZE.json');obs=e.read(BR/'experiments'/name/'OBSERVATIONS.json')
        assert obs['prediction_sha256']==e.sha(BR/'experiments'/name/'PREDICTION_FREEZE.json')
        assert pred['time']<=obs['time']
        c=e.read(BR/'candidates'/(pred['candidate_id']+'.json'));m=Model(c['scaffold'],c['expression'])
        assert np.allclose(m.predict(pred['designs'],pred['parameter_values']),pred['predictions'])
        if obs['rows']:assert abs(rmse(m.predict(obs['rows'],pred['parameter_values']),obs['rows'])-obs['rmse'])<1e-12
        measurements.append(dict(batch=name,conditions=len(pred['designs']),observations=len(obs['rows']),rmse=obs['rmse'],prediction_before_observation=True))
    calls=list((ROOT/'calls').glob('*/completion_*.json'))+list((BR/'calls').glob('*/completion_*.json'))
    assert len(calls)==6
    usage={};no_tools=True
    for p in calls:
        c=e.read(p);assert c['returncode']==0;no_tools=no_tools and not c['tool_violations']
        for k,v in c['usage'].items():usage[k]=usage.get(k,0)+v
    initial=e.read(ROOT/'calls/01_build/input.json')
    assert initial['prior_steps']==[]
    assert 'sum(history*exp(' not in json.dumps(initial)
    available_ids={r['row_id'] for r in evidence['fit']+dev}
    refs={p.parent.name:all(ref in available_ids for ref in e.read(p)['evidence_refs']) for p in (BR/'calls').glob('*/reply.json')}
    first=e.read(BR/'calls/05_full/reply.json');last=e.read(BR/'calls/06_full/reply.json')
    assert first['experiments']!=[]
    def conditions(reply):return [(d['u'],d['h'],tuple(d['history'])) for d in reply['experiments']]
    repeated=sum(d in conditions(first) for d in conditions(last))
    oldroot=e.ROOT;e.ROOT=BR;e.verify();e.ROOT=oldroot
    result=dict(time=e.now(),scope='Organizer post-run diagnosis using observed records; no new model calls, no scientific candidate repairs, not autonomous constraint discovery',
        sources={str(p.relative_to(ROOT)):e.sha(p) for p in [BR/'visible/evidence.json',BR/'experiments/batch_1/OBSERVATIONS.json',BR/'candidates/C5.json',BR/'candidates/C6.json']},
        initial64_additive_floor=additive_bound(evidence['dev'],left,right),common80_additive_floor=add,
        independent_analytic_certificate=analytic,candidate_memberships=memberships,
        audit_checks=dict(known_cross_term_not_misclassified=True,exact_metric_recomputed=True,all_frozen_sources_unchanged=True,
                          all_six_calls_no_tool_actions=bool(no_tools),initial_prompt_no_specific_history_formula=True,
                          amendment_evidence_refs_valid=refs),prospective=measurements,
        repeated_call6_conditions=repeated,research_calls=6,usage=usage,
        finding='Both complete runnable candidates remain in the same additive class, whose best possible RMSE on all 80 development records is above 0.06. The new interaction changes history dependence but leaves the contradicted separation from waiting time intact.')
    e.write(ROOT/'POSTRUN_AUDIT.json',result)
    print(json.dumps(dict(additive_floor=add['minimum_possible_rmse'],analytic_floor=analytic['rmse_lower_bound_on_80_rows'],checks=result['audit_checks'],usage=usage),ensure_ascii=False))


if __name__=='__main__':main()
