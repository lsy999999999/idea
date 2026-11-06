"""Run frozen inquiry; recover only validated metadata layouts with separate receipts."""
from pathlib import Path
import json
import subprocess
import sys
import time

project=Path(__file__).resolve().parent.parent
run=project/'historical_inquiry/cases/fish_001/runs/inquiry_v2_live_20261106_002'
python=str(project/'.venv/bin/python')
command=[python,'-u','historical_inquiry/bounded_live_finish_20261106.py']
recovery=run/'recovery'
recovery.mkdir(exist_ok=True)
for iteration in range(20):
    n=len(list(recovery.glob('supervisor_*.log')))+1
    path=recovery/f'supervisor_{n:03d}.log'
    print(json.dumps({'supervisor_iteration':n,'status':'resume_frozen_run'}),flush=True)
    with path.open('x') as log:
        process=subprocess.Popen(command,cwd=project,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        for line in process.stdout:
            log.write(line);log.flush();print(line,end='',flush=True)
        status=process.wait()
    if status==0:
        sys.exit(0)
    state=json.loads((run/'state.json').read_text())
    candidates=[]
    for stage in (run/'stages').iterdir():
        original=stage/'attempt-001'
        if stage.name not in state['stages'] and (original/'execution_audit.json').exists() and (original/'final.txt').exists():
            candidates.append(stage)
    if len(candidates)!=1:
        raise SystemExit('Needs explicit inspection: ambiguous or missing complete raw response')
    stage=candidates[0]
    p=subprocess.run([python,'historical_inquiry/admit_live_layout_20261106.py',stage.name],cwd=project,capture_output=True,text=True)
    admission=recovery/f'supervisor_{n:03d}_admission.log'
    admission.write_text(p.stdout+p.stderr)
    print(p.stdout+p.stderr,flush=True)
    if p.returncode:
        raise SystemExit('Needs explicit inspection: metadata-only recovery did not validate')
raise SystemExit('Supervision recovery budget exhausted; preserve current state')
