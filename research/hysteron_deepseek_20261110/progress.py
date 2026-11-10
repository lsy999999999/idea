from pathlib import Path
import fcntl,json,time
R=Path(__file__).resolve().parent
G=R/'runtime/ours_source/runs/hypothesis_development_hysteron_generation'
for p in sorted(G.glob('stages/*/api_v2/workspace/ACCEPTED.json')):print('accepted',p.parent.parent.parent.name)
for group in ['ours/generation','definition_service/generation','ours/evaluation']:
 d=(R/'controller_only/model_calls/hysteron'/group) if group.startswith('definition_service') else R/'runs/hysteron'/group
 req=sorted(d.glob('*.request.json'));resp=sorted(d.glob('*.response.json'))
 if req:print(group,'calls',len(req),'responses',len(resp),'last_age_s',round(time.time()-req[-1].stat().st_mtime))
 if resp:
  r=json.loads(resp[-1].read_text());m=r['choices'][0]['message'];print(' latest',resp[-1].stem,[t['function']['name'] for t in m.get('tool_calls') or []],(m.get('content') or '')[:130])
print('log_updated_seconds_ago',round(time.time()-(R/'experiment.log').stat().st_mtime))
generation=R/'runs/hysteron/ours/generation/STATUS.json'
evaluation=R/'runs/hysteron/ours/evaluation/STATUS.json'
running=False
lock=R/'.run.lock'
if lock.exists():
    with lock.open('r') as file:
        try:
            fcntl.flock(file,fcntl.LOCK_EX|fcntl.LOCK_NB)
            fcntl.flock(file,fcntl.LOCK_UN)
        except BlockingIOError:
            running=True
print('runner_status','running' if running else 'stopped')
for name,path in [('generation',generation),('independent_evaluation',evaluation)]:
    print(name+'_status',json.loads(path.read_text()).get('status','unknown') if path.exists() else 'pending')
if evaluation.exists() and json.loads(evaluation.read_text()).get('status')=='complete':
    print('EXPERIMENT_COMPLETE')
elif not running and (R/'LAST_FAILURE.json').exists():
    print('last_failure',json.loads((R/'LAST_FAILURE.json').read_text()).get('error'))
