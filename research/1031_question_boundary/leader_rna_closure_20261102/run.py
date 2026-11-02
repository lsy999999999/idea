"""Bounded transport/state driver. Scientific model/code belongs to roles."""
import json
import sys
from pathlib import Path
import broker as b

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent/'leader_rna_v2_20261102'
RUN = ROOT/'runs/closure'
ORDER = ['L0','R0','L1','R1','L2','R2','L3']

def prepare():
    assert not RUN.exists()
    assert b.verify(BASE/'runs/V2_full'), 'Original frozen run failed verification'
    for d in ['states','inputs','replies','tools','visible','code']:
        (RUN/d).mkdir(parents=True,exist_ok=False)
    old = BASE/'runs/V2_full'
    corrections = []
    for p in sorted((old/'visible').iterdir()):
        if p.suffix not in {'.json','.md'}: continue
        if p.name == 'sequence_measurements.json':
            data = b.read(p)
            data['sample_metadata'] = dict(condition='B', measurement='DNA sequencing read fractions, not RNA concentrations', provenance='leader_rna_dev_v1_20261102/agent_visible/researcher_01.md:244', original_public_note='A is the reference template; the measured read fractions describe B.')
            b.dump(RUN/'visible'/p.name, data)
            corrections.append(dict(file=p.name,change='Restore previously public B sample mapping only',source=data['sample_metadata']['provenance'],original_sha256=b.sha(p),corrected_sha256=b.sha(RUN/'visible'/p.name)))
        else: b.dump(RUN/'visible'/p.name,p.read_text())
    st = b.state(old)
    leader = b.read(old/'sealed_replies/L6.json')
    sources = [src for t in st['tools'] for src in t['result'].get('sources',[])]
    materials = dict(case_brief=(old/'visible/case_brief.md').read_text(),original_candidate=leader['candidates'][0],original_load_calculation=next(t for t in st['tools'] if t['id']=='C3'),historical_sources=sources,metadata_corrections=corrections,provenance='Frozen public pre-review artifacts only; no prior review, target paper or late measurements',historical_forecast_status='Previous 36/48 h forecasts have already been development-scored by organizer; no fresh holdout claim permitted.')
    b.dump(RUN/'materials.json',materials)
    cfg=dict(run_id='closure',stage='C',arm='closure',model='gpt-6-luna',schedule='Focus TQ/GQ observable chain and substantive verdict; reserve actual rework after failure.',reply_cap=7,compute_cap=6,search_cap=2,evidence_cap=0,baseline_artifact_ids=['C3','E0','E1','E2','E3','E4'],created=b.now(),material_sha256=b.sha(RUN/'materials.json'),source_code_sha256=b.sha(ROOT/'broker.py'))
    b.dump(RUN/'config.json',cfg)
    candidate=leader['candidates'][0]
    task=dict(id='TQ',candidate_id='C1',gap_id='GQ',kind='mechanism',status='todo',deliverable='Compute and substantively audit original q; revise or reject with observable consequences.',acceptance='Actual q output, mathematical/physical distinction, common-age schedule comparison and explicit verdict.',evidence_refs=['C3','E0'],reason='New bounded continuation; original run remains frozen.')
    s=dict(version=-1,candidates={'C1':candidate},tasks={'TQ':task},actor_events=[],tools=[],literature_use=[],adjudications=[],opened=[p.name for p in (RUN/'visible').glob('*.json')],counters=dict(replies=0,search=0,compute=0,evidence=0),finals=[])
    b.snapshot(RUN,s,'initial reconstructed public continuation')
    b.dump(ROOT/'BASELINE_MANIFEST.json',dict(original_frozen_sha256=b.sha(old/'FROZEN.json'),original_verified=True,original_broker_sha256=b.sha(BASE/'broker.py'),corrections=corrections))
    print(json.dumps(dict(prepared=str(RUN),candidate=candidate['id'],public_sources=len(sources))))

def next_input():
    s=b.state(RUN); label=ORDER[s['counters']['replies']]
    role='leader' if label.startswith('L') else 'executor'
    assert not any(t['result']['status']=='waiting_external' for t in s['tools'])
    p=b.build_input(RUN,role,label,final=label=='L3')
    # Feedback is an explicit extra artifact, introduced only after initial audit.
    feedback=ROOT/'FEEDBACK.json'
    if feedback.exists():
        data=b.read(p);data['organizer_feedback']=b.read(feedback)
        # Input not yet dispatched; retain initial bundle then freeze actual one.
        p2=p.with_name(label+'_with_feedback.json');b.dump(p2,data);p=p2
        b.event(RUN,'feedback_input',label=label,path=str(p.relative_to(RUN)),sha256=b.sha(p))
    prompt=f"Act as RNA {role.upper()}, requested model gpt-6-luna. Read ONLY {p}. Follow the complete input instructions. Inspect it in chunks without truncating the state/tool results. Write ONE complete JSON reply to {RUN/'replies'/f'{label}.json'}. Use exec only for reading that input and writing your reply. No other file exploration, memory, network, direct scientific execution or delegation. Scientific code belongs in requests for broker execution. Finish writing once, then return a short completion notification."
    b.dump(RUN/'inputs'/f'{label}_invocation.txt',prompt)
    b.dump(RUN/'inputs'/f'{label}_dispatch.json',dict(label=label,role=role,path=str(p),sha256=b.sha(p)))
    print(prompt)

def ingest(label):
    s=b.state(RUN);assert label==ORDER[s['counters']['replies']]
    role='leader' if label.startswith('L') else 'executor'
    d=b.read(RUN/'inputs'/f'{label}_dispatch.json')
    assert b.sha(Path(d['path']))==d['sha256']
    b.complete_actor(RUN,label,role)
    s=b.ingest(RUN,label,role)
    print(json.dumps(dict(label=label,counters=s['counters'],tasks=s['tasks'],adjudications=s['adjudications'][-1:],tools=[dict(id=t['id'],status=t['result']['status'],stdout=t['result'].get('stdout','')[:1000],stderr=t['result'].get('stderr','')) for t in s['tools']]),ensure_ascii=False))

if __name__=='__main__':
    action=sys.argv[1]
    if action=='prepare':prepare()
    elif action=='next':next_input()
    elif action=='ingest':ingest(sys.argv[2])
    elif action=='freeze':
        assert b.verify(BASE/'runs/V2_full')
        assert b.sha(BASE/'runs/V2_full/FROZEN.json')==b.read(ROOT/'BASELINE_MANIFEST.json')['original_frozen_sha256']
        print(b.freeze(RUN))
    elif action=='verify':print(b.verify(RUN))
