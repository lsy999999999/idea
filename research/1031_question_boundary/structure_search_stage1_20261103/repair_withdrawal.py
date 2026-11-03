"""Correct a bounded-error counterexample construction without changing frozen source."""
import json
import experiment as e

def main():
    ev=e.read(e.ROOT/'visible/evidence.json');groups={}
    for row in ev['dev']:
        key=json.dumps([row['u'],row['h'],row['history']]);groups.setdefault(key,[]).append(row['o'])
    means={k:sum(v)/len(v) for k,v in groups.items()}
    centers={k:(max(v)+min(v))/2 for k,v in groups.items()}
    mean_error=max(abs(x-means[k]) for k,v in groups.items() for x in v)
    center_error=max(abs(x-centers[k]) for k,v in groups.items() for x in v)
    # For bounded errors, feasible location lies in [max(o)-epsilon,min(o)+epsilon].
    # A sample mean need not lie in that interval. The midrange always does when range<=2epsilon.
    assert mean_error>.015 and center_error<=.015
    correction=dict(time=e.now(),failed_implementation='experiment.py:withdrawal, sample-mean offset asserted all observed errors <=epsilon',observed_sample_mean_max_error=mean_error,corrected_estimator='midrange=(min+max)/2; equivalently midpoint of nonempty bounded-error feasibility interval',proof='If max(o)-min(o)<=2epsilon, midpoint has max error (max(o)-min(o))/2<=epsilon.',corrected_max_error=center_error,original_frozen_source_unchanged=True,scientific_candidates_unchanged=True,source_sha256=e.sha(__file__))
    e.write(e.ROOT/'withdrawal/IMPLEMENTATION_CORRECTION.json',correction)
    audit=e.read(e.ROOT/'withdrawal/constraint_audit_v2.json');config=e.read(e.ROOT/'withdrawal/generator_v2.json')
    result=dict(type='organizer-controlled premise invalidation test, not a fresh scientific discovery',original_evidence_unchanged=True,active_hard_constraints=len(audit['certified']),current_only_rewrite_restored=not config['disabled_operations'],parameters_only_restored=config['parameters_only'],counterexample='Underlying system o_true=0; instrument offset for each preparation equals the midpoint of that condition\'s minimum and maximum diagnostic readings. This fits within the specified bounded error after stable observation is dropped.',counterexample_max_error=center_error,noise_bound=.015,counterexample_feasible=center_error<=.015,scope='Finite diagnostic records only; establishes necessity of the observation premise; no predictive generalization claim',implementation_correction_sha256=e.sha(e.ROOT/'withdrawal/IMPLEMENTATION_CORRECTION.json'))
    assert not audit['certified'] and config['parameters_only'] and result['counterexample_feasible']
    e.write(e.ROOT/'withdrawal/RESULT.json',result)
    e.event('constraint_withdrawal_audit_corrected',result_sha256=e.sha(e.ROOT/'withdrawal/RESULT.json'))
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
