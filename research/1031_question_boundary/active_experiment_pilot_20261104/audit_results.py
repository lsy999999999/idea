"""Replay, data-flow and dependency audit. No new acquisition or inference."""
import ast
import json
from pathlib import Path
import numpy as np
import run as pilot
from model_language import Model,rmse
from experiment_tools import key,equal_features,scoped_capacity,predict

ROOT=Path(__file__).resolve().parent

def input_dependencies(c):
    m=Model(c['scaffold'],c['expression']);quantities=dict(m.qtrees)
    def visit(node):
        if isinstance(node,ast.Name):
            if node.id in quantities:return visit(quantities[node.id])
            if node.id=='history':return {'history['+str(i)+']' for i in range(4)}
            if node.id in ['u','h']:return {node.id}
            return set()
        if isinstance(node,ast.Subscript) and isinstance(node.value,ast.Name) and node.value.id=='history':return {'history['+str(node.slice.value)+']'}
        result=set()
        for child in ast.iter_child_nodes(node):result|=visit(child)
        return result
    return sorted(visit(m.tree))

def main():
    pilot.verify();checks=[]
    def check(name,value):
        assert value,name
        checks.append(dict(name=name,passed=True))
    old=pilot.read(ROOT/'visible/initial.json');aug=pilot.read(ROOT/'visible/augmented.json')
    exp=pilot.read(ROOT/'experiment/OBSERVATIONS.json');rows=exp['rows']
    frozen=pilot.read(ROOT/'experiment/PREDICTION_FREEZE.json');initial=pilot.read(ROOT/'INITIAL_MODELS.json')['candidates']
    all_models=pilot.read(ROOT/'REVISED_MODELS.json')['candidates'];by_id={c['id']:c for c in all_models}
    check('all 4 research calls completed',len(list((ROOT/'calls').glob('*/reply.json')))==4)
    for p in (ROOT/'calls').glob('*/completion_*.json'):
        result=pilot.read(p)
        check(str(p.relative_to(ROOT))+' requested authorized model',result['requested_model']=='gpt-6-luna' and result['requested_reasoning']=='low')
        check(str(p.relative_to(ROOT))+' no native tool use',not result['tool_violations'])
    check('active predictions frozen before observations',frozen['time']<=exp['time'])
    check('active observations bound to exact frozen predictions',exp['prediction_sha256']==pilot.sha(ROOT/'experiment/PREDICTION_FREEZE.json'))
    known={key(r) for r in old['fit']+old['dev']}
    check('all active conditions new',all(key(r) not in known for r in rows))
    check('exactly four active conditions and sixteen observations',len({r['design_id'] for r in rows})==4 and len(rows)==16)
    active_fit=[r for r in aug['fit'] if r['row_id'].startswith('active_')]
    active_dev=[r for r in aug['dev'] if r['row_id'].startswith('active_')]
    check('new fit repeats0/1 only',len(active_fit)==8 and all(r['repeat']<2 for r in active_fit))
    check('new dev repeats2/3 only',len(active_dev)==8 and all(r['repeat']>=2 for r in active_dev))
    check('new fit and dev row ids disjoint',not {r['row_id'] for r in active_fit}&{r['row_id'] for r in active_dev})
    for c in initial:
        check(c['id']+' frozen active predictions replay',np.max(np.abs(predict(c,frozen['designs'])-frozen['predictions'][c['id']]))<1e-10)
    for offer in pilot.read(ROOT/'EXPERIMENT_OFFERS.json'):
        a,b=offer['designs']
        for c in initial:
            check(offer['id']+'/'+c['id']+' offer predictions replay',np.max(np.abs(predict(c,[a,b])-offer['predictions'][c['id']]))<1e-10)
            check(offer['id']+'/'+c['id']+' equality certificate replay',equal_features(c['request'],a,b)==offer['symbolically_equal_features'][c['id']])
    fitted_versions=0
    for p in sorted((ROOT/'completion').glob('*.json')):
        record=pilot.read(p);ev=old if p.stem.startswith('C') else aug
        for i,c in enumerate(record['candidates']):
            check(p.stem+'/'+str(i)+' fit replay',abs(rmse(predict(c,ev['fit']),ev['fit'])-c['train_rmse'])<1e-9)
            check(p.stem+'/'+str(i)+' dev replay',abs(rmse(predict(c,ev['dev']),ev['dev'])-c['dev_rmse'])<1e-9)
            check(p.stem+'/'+str(i)+' parameter binding',len(c['values'])==len(c['scaffold']['parameters'])<=8)
            fitted_versions+=1
        check(p.stem+' residual budget',record['budget_after']['residual_calls']<=6400)
    for stage,ev in [('initial',old),('augmented',aug)]:
        data=pilot.read(ROOT/'baseline'/(stage+'.json'))
        check('baseline '+stage+' residual budget',data['budget']['residual_calls']<=1600)
        for i,c in enumerate(data['candidates']):
            check('baseline '+stage+'/'+str(i)+' fit replay',abs(rmse(predict(c,ev['fit']),ev['fit'])-c['train_rmse'])<1e-9)
            check('baseline '+stage+'/'+str(i)+' dev replay',abs(rmse(predict(c,ev['dev']),ev['dev'])-c['dev_rmse'])<1e-9)
    selection=pilot.read(ROOT/'FINAL_SELECTION_FREEZE.json');conf=pilot.read(ROOT/'CONFIRMATION_PREDICTIONS.json');observed=pilot.read(ROOT/'CONFIRMATION_OBSERVATIONS.json')
    check('final selection precedes confirmation acquisition',selection['time']<=conf['time']<=observed['time'])
    check('selection marked no hidden read',selection['hidden_read'] is False)
    check('confirmation bound to exact selected forecasts',observed['forecast_sha256']==pilot.sha(ROOT/'CONFIRMATION_PREDICTIONS.json'))
    for arm,c in selection['arms'].items():
        if c:check(arm+' confirmation replay',np.max(np.abs(predict(c,conf['designs'])-conf['predictions'][arm]))<1e-10)
    dependencies={c['id']:input_dependencies(c) for c in all_models}
    common_ignored=[coord for coord in ['u','h']+['history['+str(i)+']' for i in range(4)] if all(coord not in input_dependencies(c) for c in initial)]
    first=pilot.read(ROOT/'calls/01_propose/reply.json')['proposals']
    fingerprints=[json.dumps(pilot.request_of(p),sort_keys=True) for p in first]
    caps={c['id']:scoped_capacity(c['request'],aug['dev'],rows,aug['metadata']) for c in all_models}
    report=dict(time=pilot.now(),checks=checks,checks_passed=len(checks),fitted_agent_versions_replayed=fitted_versions,
        initial_proposals=len(first),unique_initial_feature_requests=len(set(fingerprints)),actual_input_dependencies=dependencies,
        inputs_ignored_by_every_initial_fitted_model=common_ignored,
        R1_same_representation_and_degree_as_C0=by_id.get('R1',{}).get('request')==by_id['C0']['request'],
        scoped_capacities=caps,hard_class_exclusions=sum(not v['completion_enabled'] for v in caps.values()),
        starting_model_expanded_dev_rmse=rmse(predict(by_id['C0'],aug['dev']),aug['dev']),
        findings=['Initial proposals C1/C2 are duplicate feature requests and both fit to the same intercept-plus-u expression.',
          'Only h and history[3] generated offered disagreement above0.06; all initial fitted models ignore history[1]/history[2].',
          'Selected experiments refute frozen fitted instances but do not create a hard feature-class exclusion.',
          'R1 returns to the starting feature representation and degree; its changed terms/coefficients are within that class.',
          'Experiment suggestions came from the tool; the agent selected two suggestions and supplied no manual pair.',
          'Expanded dev uses fresh repeats of training conditions; final hidden/random confirmation provides design-level generalization.',
          'One active development chain with shared-observation tool baseline does not isolate a causal benefit of active experimentation.'])
    pilot.write(ROOT/'POSTRUN_AUDIT.json',report)
    print(json.dumps(dict(checks=len(checks),common_ignored=common_ignored,unique_initial=len(set(fingerprints)),hard_class_exclusions=report['hard_class_exclusions'],starting_expanded_dev=report['starting_model_expanded_dev_rmse'])))

if __name__=='__main__':main()
