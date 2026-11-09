"""Serial runner with explicit phases; loading configuration does not call the model."""
from pathlib import Path
import argparse,json,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--cases',nargs='+',default=['wave'],choices=['wave','optical']);p.add_argument('--systems',nargs='+',default=['researchagent','virtual_lab','scientist_v2','evoscientist','ours'],choices=['researchagent','virtual_lab','scientist_v2','evoscientist','ours']);p.add_argument('--phases',nargs='+',default=['generation','correction'],choices=['generation','correction']);p.add_argument('--execute',action='store_true');p.add_argument('--knowledge',choices=['online','closed'],default=json.loads((ROOT/'model_config.json').read_text()).get('knowledge','online'));a=p.parse_args()
jobs=[]
for case in a.cases:
 for system in a.systems:
  for phase in a.phases:
   runner={'ours':'run_ours.py','scientist_v2':'drive_scientist.py','evoscientist':'run_evo.py'}.get(system,'run_discussion_systems.py')
   cmd=[sys.executable,str(ROOT/'runtime'/runner),'--case',case,'--phase',phase]
   if system in ['researchagent','virtual_lab']:cmd+=['--system',system]
   if system=='ours':cmd+=['--knowledge',a.knowledge]
   jobs.append((case,system,phase,cmd))
if not a.execute:
 print(json.dumps({'status':'dry_run_no_model_calls','model':json.loads((ROOT/'model_config.json').read_text())['model'],'jobs':[j[3] for j in jobs]},indent=2));raise SystemExit
if any(system not in {'ours','researchagent','virtual_lab'} for system in a.systems):
 p.error('Historical cases block unrestricted shell/server adapters until their external access is mechanically screened')
endpoint=ROOT/'gateway_endpoint.json'
if endpoint.exists():p.error('An endpoint file already exists. Confirm its process is stopped, then archive/remove the stale endpoint before starting a new suite.')
log=(ROOT/'suite_gateway.log').open('w')
gateway=subprocess.Popen([sys.executable,str(ROOT/'runtime/model_gateway.py')],stdout=log,stderr=subprocess.STDOUT)
try:
 for _ in range(100):
  if endpoint.exists():break
  if gateway.poll() is not None:raise RuntimeError('Gateway failed; inspect suite_gateway.log')
  time.sleep(.1)
 else:raise TimeoutError('Gateway did not start')
 for case,system,phase,cmd in jobs:
  status=ROOT/'runs'/case/system/phase/'STATUS.json'
  if status.exists():
   print('Skip existing account; use a fresh replay folder for a new experiment:',case,system,phase,flush=True);continue
  with (ROOT/f'{case}_{system}_{phase}.log').open('w') as out:subprocess.run(cmd,stdout=out,stderr=subprocess.STDOUT,check=True)
  print(case,system,phase,json.loads(status.read_text())['status'] if status.exists() else 'missing_status',flush=True)
finally:
 gateway.terminate();gateway.wait(timeout=10);log.close()
 if endpoint.exists() and json.loads(endpoint.read_text()).get('pid')==gateway.pid:endpoint.unlink()
