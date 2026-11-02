"""Post-run provenance audit; does not choose or repair a scientific model."""
import json
from pathlib import Path
import broker as b
from run import ROOT, BASE, RUN, ORDER

def main():
    s=b.state(RUN)
    records=[]
    for e in s['actor_events']:
        label=e['label'];d=b.read(RUN/'inputs'/f'{label}_dispatch.json')
        completion=b.read(RUN/'actor_finished'/f'{label}.json')
        records.append(dict(label=label,input_hash_matches=b.sha(Path(d['path']))==d['sha256']==e['input_sha256'],reply_hash_matches=b.sha(RUN/'sealed_replies'/f'{label}.json')==b.sha(RUN/'replies'/f'{label}.json')==e['reply_sha256']==completion['sha256'],protocol_errors=e['protocol_errors']))
    tools=[]
    for t in s['tools']:
        item=dict(id=t['id'],status=t['result']['status'],type=t['type'],candidate_id=t.get('candidate_id'),gap_id=t.get('gap_id'))
        if t['type']=='compute':
            code=RUN/'tools'/t['id']/'submitted.py'
            item['submitted_code_matches_request']=code.read_text()==t['request']['code']
            item['execution_code_hash_matches']=b.sha(code)==t['result'].get('code_sha256')
            item['stdout_json_valid']=False
            try:json.loads(t['result'].get('stdout',''));item['stdout_json_valid']=True
            except (ValueError,TypeError):pass
        tools.append(item)
    manifest=b.read(ROOT/'IMPLEMENTATION_MANIFEST.json')
    effective=dict(manifest['files'])
    patches=[]
    for p in sorted(ROOT.glob('IMPLEMENTATION_PATCH_*.json')):
        patch=b.read(p);assert effective[patch['file']]==patch['previous_sha256']
        effective[patch['file']]=patch['new_sha256'];patches.append(patch)
    result=dict(time=b.now(),original_v2_frozen_unchanged=b.verify(BASE/'runs/V2_full') and b.sha(BASE/'runs/V2_full/FROZEN.json')==b.read(ROOT/'BASELINE_MANIFEST.json')['original_frozen_sha256'],original_broker_unchanged=b.sha(BASE/'broker.py')==b.read(ROOT/'BASELINE_MANIFEST.json')['original_broker_sha256'],effective_implementation_manifest_matches=all(b.sha(ROOT/n)==h for n,h in effective.items()),interface_patches=patches,order_matches=[e['label'] for e in s['actor_events']]==ORDER[:len(s['actor_events'])],within_reply_budget=s['counters']['replies']<=7,within_compute_budget=s['counters']['compute']<=6,within_search_budget=s['counters']['search']<=2,actor_records=records,tools=tools,task_status=s['tasks']['TQ']['status'],adjudications=s['adjudications'],executor_adjudication_labels=[e['label'] for e in s['actor_events'] if e['role']=='executor' and e['reply'].get('adjudication')],organizer_counterexample_feedback_supplied=(ROOT/'FEEDBACK.json').exists(),limitations=['application-level input allowlist, not OS isolation','fresh reconstructed contexts, not exact replay','model requested gpt-6-luna; underlying weights and token/billing totals not independently verified','organizer knows prior failure; substantive audit is nonblind','input/public-source hashes establish provenance, not scientific validity'])
    b.dump(ROOT/'PROVENANCE_AUDIT.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in {'adjudications','limitations'}},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
