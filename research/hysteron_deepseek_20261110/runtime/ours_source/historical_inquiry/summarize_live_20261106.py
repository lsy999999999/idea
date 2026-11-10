"""Read-only evidence inventory of the supervised fish inquiry, saved outside generation."""
from pathlib import Path
import hashlib
import json

here=Path(__file__).resolve().parent
run=here/'cases/fish_001/runs/inquiry_v2_live_20261106_002'
def load(p): return json.loads(p.read_text())
def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
state=load(run/'state.json')
rows=[]
for sid in state['stages']:
    p=run/'stages'/sid/'result.json'
    a=load(p)
    original=run/'stages'/sid/'attempt-001/prompt.txt'
    role=original.read_text().split('ROLE: ',1)[1].split('\n',1)[0]
    rows.append({'stage':sid,'role':role,'summary':a.get('summary'),
        'personal_question':a.get('initial_question') or a.get('personal_question_update'),
        'shared_question_update':a.get('shared_question_update'),
        'learning_request':a.get('learning_request'),
        'top_level_analysis_plan':a.get('analysis_plan'),
        'exploration':a.get('exploration'),
        'learning_change':a.get('learning_change'),
        'memory_notes':[{'key':n['key'],'mastery':n['mastery']} for n in a.get('memory_notes',[])],
        'result':str(p.resolve()),'sha256':digest(p)})
replies=[(p,load(p)) for p in (run/'broker').glob('*.json')]
requests=[{'boundary':p.stem,'source_count':len(a.get('sources',[])),
    'source_ids':[s['id'] for s in a.get('sources',[])],
    'operations_requested':len(a['request'].get('operations',[])),
    'computed':a.get('computed',[]),
    'knowledge_status':(a.get('knowledge') or {}).get('status')} for p,a in replies]
protected=load(here/'fix_checks_20261105/PROTECTED_BEFORE.json')
changed=[p for p,h in protected.items() if not Path(p).is_file() or digest(p)!=h]
freeze=load(run/'GENERATION_FREEZE.json') if (run/'GENERATION_FREEZE.json').exists() else None
sources={s['id']:s for p,a in replies for s in a.get('sources',[])}
restriction=load(here/'cases/fish_001/controller_only/restriction.json')
origin=restriction['source_paper']; tokens=[origin['title'].casefold(),origin['id'].replace('https://doi.org/','').casefold()]
prompts=list((run/'stages').glob('*/attempt-*/prompt.txt'))
hits=[str(p) for p in prompts if any(t in p.read_text().casefold() for t in tokens)]
audits=[(p,load(p)) for p in (run/'stages').glob('*/attempt-*/execution_audit.json')]
old=here/'cases/fish_001/runs/inquiry_v2_live_20261106_001'
old_audits=[(p,load(p)) for p in (old/'stages').glob('*/attempt-*/execution_audit.json')]
summary={'status':state.get('status','in_progress'),'run':str(run.resolve()),
    'supervised_budget_amendment':load(run/'recovery/BOUNDED_CONTINUATION_AMENDMENT.json'),
    'substantive_novelty_review_complete':load(run/'evaluation/ACCEPTED_CHECK.json').get('substantive_novelty_review_complete',True) if (run/'evaluation/ACCEPTED_CHECK.json').exists() else False,
    'accepted_stages':len(rows),'accepted_learning_stages':sum('_learn_' in v['stage'] for v in rows),
    'top_level_plans_proposed':sum(isinstance(v['top_level_analysis_plan'],dict) for v in rows),
    'operations_requested_in_broker':sum(v['operations_requested'] for v in requests),
    'additional_broker_operation_results':sum(len(v['computed']) for v in requests),
    'additional_successful_broker_computations':sum(c.get('result',{}).get('status')=='executed' for v in requests for c in v['computed']),
    'pending_broker_computations':sum(c.get('result',{}).get('status')=='pending_controller' for v in requests for c in v['computed']),
    'initial_sample_windows_returned':len(load(run/'initial_materials.json')['sampled_windows']['computed']),
    'initial_foundation_sources':len(load(run/'initial_materials.json')['source_catalog']),
    'distinct_sources_returned':len(sources),
    'source_date_violations':[s['id'] for s in sources.values() if not s.get('date') or s['date']>='2010-01-01'],
    'forbidden_identity_hits_in_generation_prompts':hits,
    'generation_attempt_audit_files':len(audits),'reused_execution_records':sum(a.get('model_call_performed_in_this_run') is False for p,a in audits),
    'physical_audited_generation_calls_across_both_runs':sum(a.get('model_call_performed_in_this_run') is not False for p,a in audits+old_audits),
    'generation_tool_events':sum(a['tool_events'] for p,a in audits+old_audits),
    'execution_planner_audits':[load(p) for p in (run/'services/analysis').glob('*/planner-attempt-*/execution_audit.json')],
    'protected_baseline_files':len(protected),'changed_protected_baseline_files':changed,
    'generation_frozen':bool(freeze),
    'changed_frozen_generation_files':[p for p,h in freeze['files'].items() if digest(p)!=h] if freeze else [],
    'stages':rows,'requests':requests,
    'sources':[{'id':s['id'],'date':s['date'],'title':s['title'],'doi':s['doi'],'access':s['access']} for s in sources.values()]}
out=here/'LIVE_TRIAL_20261106_EVIDENCE.json'
out.write_text(json.dumps(summary,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in summary.items() if k not in {'stages','requests','sources','supervised_budget_amendment'}},ensure_ascii=False,indent=2))
