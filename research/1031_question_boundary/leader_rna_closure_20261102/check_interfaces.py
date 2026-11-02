"""Zero-model regression of observed RNA V2 interface failures."""
import json
import tempfile
from pathlib import Path
import broker as b

def main():
    base=b.ROOT.parent/'leader_rna_v2_20261102/runs/V2_full'
    old=b.state(base)
    historical=[src for t in old['tools'] for src in t['result'].get('sources',[])]
    with tempfile.TemporaryDirectory(prefix='rna_closure_interfaces_') as td:
        run=Path(td)
        for d in ['states','inputs','replies','tools','visible']:(run/d).mkdir()
        cfg=dict(stage='C',reply_cap=5,compute_cap=2,search_cap=0,baseline_artifact_ids=['E3','E4','C3'])
        b.dump(run/'config.json',cfg);b.dump(run/'materials.json',dict(historical_sources=historical))
        task=dict(id='TQ',candidate_id='C1',gap_id='GQ',kind='mechanism',status='executing')
        s=dict(version=-1,candidates={'C1':old['candidates']['C1']},tasks={'TQ':task},actor_events=[],tools=[],literature_use=[],adjudications=[],counters=dict(replies=0,compute=0,search=0,evidence=0),finals=[])
        b.snapshot(run,s,'interface fixture only')
        available=b.available_artifacts(run,s,cfg)
        assert {'R5_S1','R5_S2','E3','E4','C3'}<=available
        assert 'R5_S999' not in available
        result=b.process_request(run,dict(type='compute',id='fixture_calc',candidate_id='C1',gap_id='GQ',model_spec='transport fixture, not a scientific model',code='import json\nprint(json.dumps({"fixture":True}))'))
        assert result['result']['status']=='executed'
        assert b.state(run)['tasks']['TQ']['status']=='acceptance'
        # Actual V2 source identifiers can now support an explicit refusal/rework.
        label='Ltest';b.dump(run/'inputs'/f'{label}.json',{})
        reply=dict(candidates=[],tasks=[],requests=[],adjudication=dict(task_id='TQ',decision='rework',artifact_ids=['R5_S1','R5_S2'],checks=['Sources exist; source interpretation does not close main observable task.'],reason='fixture'),final=None)
        b.dump(run/'replies'/f'{label}.json',reply);b.complete_actor(run,label,'leader','zero-model fixture')
        got=b.ingest(run,label,'leader')
        assert got['adjudications'][-1]['formal_gate']
        assert got['tasks']['TQ']['status']=='rework'
        # Computation for a different gap cannot satisfy TQ's mechanism gate.
        wrong=b.process_request(run,dict(type='compute',id='wrong_gap',candidate_id='C1',gap_id='OTHER',model_spec='wrong-gap fixture',code='import json\nprint(json.dumps({"fixture":True}))'))
        assert wrong['result']['status']=='executed'
        b.dump(run/'inputs/Lwrong.json',{})
        reply['adjudication']=dict(task_id='TQ',decision='complete',artifact_ids=['wrong_gap'],checks=['fixture'])
        b.dump(run/'replies/Lwrong.json',reply);b.complete_actor(run,'Lwrong','leader','zero-model fixture')
        got=b.ingest(run,'Lwrong','leader')
        assert not got['adjudications'][-1]['formal_gate']
        assert got['tasks']['TQ']['status']=='rework'
    report=dict(passed=True,model_calls=0,checks=['actual V2 R5_S1/R5_S2 references resolve; invented reference rejected','executed computation leaves main task awaiting acceptance','leader rework survives and can be dispatched again','wrong-gap compute cannot complete main mechanism task','object adjudication supported as documented'],scope='Interface regression only; fixtures contain no model and do not validate scientific reasoning.')
    b.dump(b.ROOT/'INTERFACE_CHECK.json',report)
    print(json.dumps(report))

if __name__=='__main__':main()
