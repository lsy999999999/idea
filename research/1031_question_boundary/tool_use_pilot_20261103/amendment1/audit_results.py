"""Post-run replay and semantic audit; does not generate or select models."""
import json
from pathlib import Path
import numpy as np
import run as pilot
from model_language import Model,rmse

ROOT=Path(__file__).resolve().parent

def main():
    pilot.verify();ev=pilot.read(ROOT/'visible/evidence.json');checks=[]
    def check(name,value):
        assert value,name
        checks.append(dict(name=name,passed=True))
    count=0
    for arm in ['direct','tool_only','agent_tools']:
        data=pilot.read(ROOT/'arms'/(arm+'.json'))
        check(arm+' residual budget',data['budget']['residual_calls']<=4800)
        check(arm+' linear budget',data['budget']['linear_solves']<=20000)
        for c in data['pool']:
            m=Model(c['scaffold'],c['expression'])
            check(c['id']+' fit replay',abs(rmse(m.predict(ev['fit'],c['values']),ev['fit'])-c['train_rmse'])<1e-9)
            check(c['id']+' dev replay',abs(rmse(m.predict(ev['dev'],c['values']),ev['dev'])-c['dev_rmse'])<1e-9)
            check(c['id']+' parameter binding',len(c['values'])==len(c['scaffold']['parameters'])<=8)
            count+=1
    selection=pilot.read(ROOT/'SELECTION_FREEZE.json');forecast=pilot.read(ROOT/'PREDICTION_FREEZE.json');obs=pilot.read(ROOT/'NEW_OBSERVATIONS.json')
    check('selection precedes forecast and observations',selection['time']<=forecast['time']<=obs['time'])
    check('selection declared no hidden read',selection['hidden_read'] is False)
    check('forecast bound to frozen selection',forecast['selection_sha256']==pilot.sha(ROOT/'SELECTION_FREEZE.json'))
    check('observations bound to frozen forecasts',obs['prediction_sha256']==pilot.sha(ROOT/'PREDICTION_FREEZE.json'))
    for arm,c in selection['selected'].items():
        if c:
            check(arm+' prospective values replay',np.max(np.abs(Model(c['scaffold'],c['expression']).predict(forecast['designs'],c['values'])-forecast['predictions'][arm]))<1e-10)
    usage={};llm_calls=0;seconds=0.
    for root in [ROOT.parent,ROOT]:
        for p in (root/'calls').glob('*/completion_*.json'):
            r=pilot.read(p);check(str(p.relative_to(ROOT.parent))+' no native tool violations',not r['tool_violations'])
            check(str(p.relative_to(ROOT.parent))+' requested authorized model',r['requested_model']=='gpt-6-luna' and r['requested_reasoning']=='low')
            seconds+=r['seconds']
            llm_calls+=r['returncode']==0
            for k,v in r['usage'].items():usage[k]=usage.get(k,0)+v
    first=pilot.read(ROOT/'steps/agent_tools_1.json')['execution']['result']
    second=pilot.read(ROOT/'calls/05_agent_tools/reply.json')
    check('rejected collision representation',first['minimum_possible_dev_rmse']>.06 and not first['can_meet_threshold'])
    check('agent added current drive after rejection','u' in second['features'])
    final=pilot.read(ROOT/'calls/06_agent_tools/reply.json')
    check('final original proposal retains semantic inconsistency','cos(' in final['quantities'][0]['expression'] and 'exp(' in final['prospective_contrast'])
    new_designs=sum(r['source']=='proposed_confirmation' for r in forecast['designs'])
    pilot.write(ROOT/'POSTRUN_AUDIT.json',dict(time=pilot.now(),checks=checks,complete_fit_versions_replayed=count,
       total_successful_research_calls=llm_calls,total_usage=usage,total_inference_seconds=seconds,
       novel_agent_confirmation_conditions=new_designs,rejected_confirmation_requests=len(forecast['rejected']),
       findings=['Initial run invalidated by organizer log-directory bug; preserved separately.',
        'Agent repaired a proved feature collision by adding u, but subsequent fitted model still failed.',
        'Last agent request references undeclared tau and describes exp weighting while implementing cos.',
        'Tool-only selected law includes multiple history terms; predictive success does not uniquely recover a mechanism.',
        'All proposed follow-up conditions duplicated existing observations, so confirmation is organizer-random only.',
        'Fit versions are internal search results, not independent LLM ideas. No method superiority estimate.']))
    print(json.dumps(dict(checks=len(checks),fit_versions=count,research_calls=llm_calls,usage=usage)))

if __name__=='__main__':main()
