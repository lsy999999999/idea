"""Collect bounded results and verify artifact bindings without further model calls."""
import json
import numpy as np
import experiment as e

def main():
    root=e.ROOT;br=root/'revision_R1';dev=e.read(root/'DEVELOPMENT_RESULTS.json');rd=e.read(br/'DEVELOPMENT_RESULTS.json');ri=e.read(br/'INDEPENDENT_RESULTS.json')['results']
    usage={};attempts=[]
    for p in sorted((root/'calls').glob('*/completion_*.json')):
        c=e.read(p);attempts.append(dict(label=p.parent.name,attempt_file=p.name,returncode=c['returncode'],tool_violations=c['tool_violations']))
        for k,v in c['usage'].items():
            if isinstance(v,(int,float)):usage[k]=usage.get(k,0)+v
    checks=dict(successful_calls_within_six=sum(c['returncode']==0 for c in attempts)==6,no_research_tool_access=all(not c['tool_violations'] for c in attempts),implementation_checks_pass=e.read(root/'IMPLEMENTATION_CHECKS.json')['passed'],withdrawal_audited=e.read(root/'withdrawal/RESULT.json')['counterexample_feasible'])
    commands=[e.read(p) for p in (root/'calls').glob('*/command_*.json')]
    checks['all_requests_luna_low']=all('--model' in c and c[c.index('--model')+1]=='gpt-6-luna' and 'model_reasoning_effort="low"' in c for c in commands)
    # Independent replay of actual frozen R1 forecasts and evaluation bindings.
    converted=e.read(br/'converted_candidates_with_failures.json');forecast=e.read(br/'PREDICTION_FREEZE.json');new=e.read(br/'NEW_EXPERIMENT.json')
    checks['revision_forecasts_precede_observations']=forecast['time']<new['time']
    checks['revision_forecasts_bound']=e.sha(br/'PREDICTION_FREEZE.json')==new['prediction_freeze_sha256']
    checks['revision_hidden_selection_bound']=e.sha(br/'SELECTION_FREEZE.json')==e.read(br/'INDEPENDENT_RESULTS.json')['selection_sha256']
    replay=[]
    hidden=e.read(br/'evaluator_only/hidden.json')
    for i,(c,fit) in enumerate(zip(converted,rd)):
        if not c:continue
        pred=e.predictor(c);p=fit['parameters'];actual=pred(forecast['designs'],p)
        ferr=float(np.max(np.abs(actual-forecast['predictions'][i]['predictions'])))
        hidden_rmse=float(np.sqrt(np.mean((pred(hidden,p)-[x['o'] for x in hidden])**2)))
        delta=abs(hidden_rmse-ri[i]['hidden_rmse']);replay.append(dict(id=c['id'],forecast_max_delta=ferr,hidden_rmse_delta=delta))
    checks['numeric_forecasts_and_scores_reproduce']=all(x['forecast_max_delta']<1e-12 and x['hidden_rmse_delta']<1e-12 for x in replay)
    # Check that fresh matched-input evidence actually supports the recorded conditional rule.
    means={}
    for x in e.read(root/'NEW_EXPERIMENT.json')['rows']:means.setdefault(x['id'],[]).append(x['o'])
    gaps={a+'_'+b:abs(float(np.mean(means[a])-np.mean(means[b]))) for a,b in [('E1','E3'),('E2','E4'),('E5','E7')]}
    checks['fresh_history_contrasts_exceed_bound']=all(v>.03 for v in gaps.values())
    checks['unseen_revision_designs']=not set(x['id'] for x in e.read(root/'PREDICTION_FREEZE.json')['designs']).intersection(x['id'] for x in forecast['designs'])
    checks['hidden_datasets_differ']=e.sha(root/'evaluator_only/hidden.json')!=e.sha(br/'evaluator_only/hidden.json')
    assert all(checks.values()),checks
    summary=dict(time=e.now(),stage='one controlled development case and one separate revision branch',scientific_acceptance='failed',stage2_go=False,reason='No candidate passed the predeclared dev and independent prediction gates; syntax, parameter binding, semantic alignment and generator-control implementation require repair.',model_requested='gpt-6-luna',reasoning_requested='low',successful_research_calls=6,total_runtime_attempts=len(attempts),raw_proposals=9,initial_F=dict(raw=3,independently_valid=0),initial_G=dict(raw=3,independently_valid=0),revision=dict(raw=3,converted=2,independently_valid=0,best_dev_rmse=rd[2]['dev_rmse'],best_hidden_rmse=ri[2]['hidden_rmse'],best_new_experiment_rmse=ri[2]['new_experiment_rmse']),predeclared_rmse_threshold=.06,usage=usage,new_observation_count=40,fit_rows=36,dev_rows=24,hidden_rows_per_batch=128,actual_fit_residual_calls=sum(x.get('residual_evaluations',0) for x in rd),fresh_matched_history_mean_gaps=gaps,implementation_and_binding_checks=checks,score_replay=replay,scientific_limits=['single curated controlled development case','explicit exponential history syntax example in first-round schema; no unprompted variable-discovery claim','measurement/determinism conditions supplied by simulator, not independently established by real instrument calibration','original matching-description validator failed approximate-match stress test; separate v2 check corrected','typed arity schema locally verified for next run, not rerun on research model','withdrawal uses labeled organizer premise invalidation, not autonomous discovery','no F/G efficacy or world originality established'],reports=['REPORT_CN.md','LITERATURE_REVIEW_CN.md','NEXT_STEP.md'])
    e.write(root/'FINAL_SUMMARY.json',summary)
    e.write(root/'RUN_ATTEMPTS.json',attempts)
    # The supplied plan remains separate from experiment results; keep its current hash as a pointer.
    e.write(root/'PLAN_REFERENCE.json',dict(path='../ideasuggest.md',sha256=e.sha(root.parent/'ideasuggest.md'),experiment_protocol_sha256=e.sha(root/'PROTOCOL.md')))
    print(json.dumps(summary,ensure_ascii=False))

if __name__=='__main__':main()
