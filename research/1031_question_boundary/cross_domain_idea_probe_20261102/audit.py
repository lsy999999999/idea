"""Provenance/count audit only; substantive idea ratings are separately authored."""
import json
from pathlib import Path
import harness as h

def verify_files(root,manifest):
    return all((root/name).exists() and h.sha(root/name)==digest for name,digest in manifest.items())

def audit():
    design=h.read(h.ROOT/'FROZEN_DESIGN.json');patch=h.read(h.ROOT/'TRANSPORT_PATCH.json')
    assert h.sha(h.ROOT/'code_versions/harness_initial.py')==design['harness_sha256']==patch['previous_harness_sha256']
    assert h.sha(h.ROOT/'harness.py')==patch['effective_harness_sha256']
    assert h.sha(h.ROOT/'PROTOCOL.md')==design['protocol_sha256'] and h.sha(h.ROOT/'ROLE.md')==design['role_sha256']
    core_pairs={};runs=[];totals=dict(role_replies=0,initial_candidates=0,compute_requests=0,compute_success=0,compute_failure=0,search_requests=0,search_success=0,search_failure=0,cli_calls=0,collaboration_calls=0)
    for run in sorted((h.ROOT/'runs').iterdir()):
        cfg=h.read(run/'config.json');s=h.state(run);frozen=run/'FROZEN.json'
        input_records=[];cli_commands=[]
        for reply in s['replies']:
            label=reply['label'];dispatch=h.read(run/'inputs'/f'{label}_dispatch.json');done=h.read(run/'finished'/f'{label}.json')
            assert h.sha(Path(dispatch['input_path']))==dispatch['input_sha256']==reply['input_sha256']
            assert h.sha(run/'sealed_replies'/f'{label}.json')==h.sha(run/'replies'/f'{label}.json')==done['sha256']==reply['reply_sha256']
            cli=run/'inputs'/f'{label}_cli_completion.json';transport='collaboration'
            if cli.exists():
                transport='CLI';totals['cli_calls']+=1
                status=h.read(cli);assert status['returncode']==0 and status['reply_json_valid']
                for line in (run/'inputs'/f'{label}_cli_events.jsonl').read_text().splitlines():
                    try:event=json.loads(line)
                    except ValueError:continue
                    item=event.get('item',{})
                    if event.get('type')=='item.completed' and item.get('type')=='command_execution':
                        cmd=item.get('command','')
                        cli_commands.append(dict(label=label,command_start=cmd[:180],exit_code=item.get('exit_code'),forbidden_memory_path=any(term in cmd for term in ['/memories/','SHARED_MEMORY','raw_memories','config.toml','auth.json'])))
            else:totals['collaboration_calls']+=1
            input_records.append(dict(label=label,transport=transport,hashes_match=True))
        totals['role_replies']+=len(s['replies'])
        first=s['replies'][0]['reply'] if s['replies'] else {}
        totals['initial_candidates']+=len(first.get('candidates',[]))
        tools=[]
        for tool in s['tools']:
            typ=tool['type'];res=tool['result'];totals[typ+'_requests']+=1
            success=res['status'] in {'executed','returned'};totals[typ+('_success' if success else '_failure')]+=1
            record=dict(id=tool['id'],type=typ,status=res['status'])
            if typ=='compute':
                p=run/'tools'/tool['id']/'submitted.py'
                assert p.read_text()==tool['request']['code'] and h.sha(p)==res['code_sha256']
                assert res['data_sha256']==cfg['data_sha256']
                try:json.loads(res.get('stdout',''));record['stdout_json_valid']=True
                except (ValueError,TypeError):record['stdout_json_valid']=False
                record['stdout_truncated']=res.get('stdout_truncated',False)
            if typ=='search' and res['status']=='returned':
                assert h.sha(run/'tools'/tool['id']/'raw.json')==res['raw_sha256']
                record['sources']=len(res['sources'])
                record['with_abstract']=sum(bool(src['original_abstract']) for src in res['sources'])
            tools.append(record)
        assert h.sha(Path(cfg['core_path']))==cfg['core_sha256']
        assert h.sha(Path(cfg['data_path']))==cfg['data_sha256']
        core_pairs.setdefault(cfg['case_id'],[]).append(cfg['core_sha256'])
        manifest_ok=frozen.exists() and verify_files(run,h.read(frozen)['files'])
        runs.append(dict(run=run.name,completed=s['counters']['replies']==3,initial_candidate_count=len(first.get('candidates',[])),within_tool_budget=s['counters']['compute']<=1 and s['counters']['search']<=1,input_reply_records=input_records,tools=tools,frozen_manifest_verified=manifest_ok,cli_command_audit=cli_commands,final_status=(s['final'] or {}).get('status'),blocked=(run/'TRANSPORT_FAILURE.json').exists()))
    prior=h.read(h.ROOT/'PRIOR_HISTORY_HASHES.json')
    report=dict(time=h.now(),totals=totals,all_12_complete=all(r['completed'] for r in runs),all_initial_triples=all(r['initial_candidate_count']==3 for r in runs),all_manifests_verified=all(r['frozen_manifest_verified'] for r in runs),all_repeat_core_hashes_equal=all(len(values)==2 and len(set(values))==1 for values in core_pairs.values()),all_prior_frozen_manifest_hashes_unchanged=all(h.sha(Path(name))==digest for name,digest in prior.items()),frozen_scientific_design_unchanged=True,recorded_transport_amendment=True,runs=runs,limitations=['Semantic idea quality is separate from this audit','CLI and collaboration outer runtime differ; no transport or model-compute comparison','CLI command scan is a lightweight path audit, not OS isolation proof','Dataset sampling, two repetitions and nonblind organizer review limit scope'])
    h.dump(h.ROOT/'PROVENANCE_AUDIT.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in {'runs','limitations'}},indent=2))

if __name__=='__main__':audit()
