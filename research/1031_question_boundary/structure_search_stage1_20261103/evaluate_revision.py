"""Evaluate every sealed raw tree independently, including malformed submissions."""
import json
import numpy as np
import experiment as e
import revision as r

BR=r.BR

def main():
    # The original converter aborted at its first invalid tree. Preserve that source/output,
    # and count each submission separately without changing any submitted scientific content.
    raw=e.read(BR/'raw_candidates.json')['candidates'];converted=[];conversion=[]
    for c in raw:
        try:
            expr=r.expression(c['tree'])
            converted.append(dict(c,expression=expr,quantities=[],quantity_annotations=c['quantities']))
            conversion.append(dict(id=c['id'],status='converted',expression=expr))
        except Exception as exc:
            converted.append(None)
            conversion.append(dict(id=c['id'],status='invalid_tree',error_type=type(exc).__name__,reason='Tree violates the declared operator arity; raw tree preserved; no scientific auto-repair'))
    e.write(BR/'CONVERSION_AUDIT.json',dict(time=e.now(),implementation_correction='Original batch conversion stopped after first malformed submission; evaluate all original submissions independently instead.',source_sha256=e.sha(__file__),candidates=conversion))
    e.write(BR/'converted_candidates_with_failures.json',converted)
    ev=e.read(e.ROOT/'visible/evidence.json');results=[]
    for c,status in zip(converted,conversion):
        results.append(e.fit_candidate(c,ev) if c else dict(status='failed',prediction_valid=False,error=status['reason']))
    e.write(BR/'DEVELOPMENT_RESULTS.json',results)
    viable=[i for i,x in enumerate(results) if x.get('dev_accepted')];selected=min(viable,key=lambda i:results[i]['dev_rmse']) if viable else None
    e.write(BR/'SELECTION_FREEZE.json',dict(time=e.now(),selected=selected,raw_candidates_sha256=e.sha(BR/'raw_candidates.json'),development_sha256=e.sha(BR/'DEVELOPMENT_RESULTS.json'),hidden_loaded=False))
    previous={x['id'] for x in e.read(e.ROOT/'PREDICTION_FREEZE.json')['designs']};designs=[x for x in ev['experiment_catalog'] if x['id'] in ['E9','E10']];assert not previous.intersection(x['id'] for x in designs)
    forecast=[]
    for c,status,fit in zip(converted,conversion,results):
        forecast.append(dict(id=status['id'],predictions=e.predictor(c)(designs,fit['parameters']).tolist() if fit.get('prediction_valid') else None))
    e.write(BR/'PREDICTION_FREEZE.json',dict(time=e.now(),designs=designs,predictions=forecast,selection_sha256=e.sha(BR/'SELECTION_FREEZE.json')))
    e.event('revision_prediction_frozen',sha256=e.sha(BR/'PREDICTION_FREEZE.json'))
    new=e.observed([dict(x,repeat=k) for x in designs for k in range(4)],19044)
    e.write(BR/'NEW_EXPERIMENT.json',dict(time=e.now(),rows=new,prediction_freeze_sha256=e.sha(BR/'PREDICTION_FREEZE.json'),scope='Fresh E9/E10; raw target and calibrated bounded observation, no candidate refitting'))
    hidden=e.read(BR/'evaluator_only/hidden.json');ind=[]
    for c,status,fit in zip(converted,conversion,results):
        row=dict(id=status['id'],selected=selected==len(ind),independently_valid=False)
        if fit.get('prediction_valid'):
            pred=e.predictor(c);p=fit['parameters'];row['hidden_rmse']=float(np.sqrt(np.mean((pred(hidden,p)-[x['o'] for x in hidden])**2)));row['new_experiment_rmse']=float(np.sqrt(np.mean((pred(new,p)-[x['o'] for x in new])**2)));row['independently_valid']=bool(fit['dev_accepted'] and row['hidden_rmse']<=.06)
        ind.append(row)
    e.write(BR/'INDEPENDENT_RESULTS.json',dict(time=e.now(),results=ind,selection_sha256=e.sha(BR/'SELECTION_FREEZE.json'),prediction_sha256=e.sha(BR/'PREDICTION_FREEZE.json'),hidden_sha256=e.sha(BR/'evaluator_only/hidden.json')))
    e.event('revision_new_evidence_obtained',sha256=e.sha(BR/'NEW_EXPERIMENT.json'))
    print(json.dumps(dict(conversion=conversion,development=results,selected=selected,independent=ind),ensure_ascii=False))

if __name__=='__main__':main()
