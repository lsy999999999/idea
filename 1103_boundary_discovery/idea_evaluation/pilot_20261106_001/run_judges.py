"""Two bounded, sequential, fresh CLI evaluations; never edit the judged source."""
import datetime
import hashlib
import json
from pathlib import Path
import signal
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parent

def dump(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')

for repeat in ['r1', 'r2']:
    run = ROOT / repeat
    if (run / 'status.json').exists():
        raise RuntimeError('Existing attempt; preserve it instead of overwriting: ' + repeat)
    cwd = Path(tempfile.mkdtemp(prefix='idea_rubric_' + repeat + '_'))
    (cwd / 'AGENTS.md').write_text('This is an isolated evaluation workspace. Respond only to the supplied scoring task. Do not use tools, read files or memories, browse, or spawn agents. Return JSON directly.\n')
    argv = ['/opt/homebrew/bin/codex','exec','--ephemeral','--skip-git-repo-check',
            '--model','gpt-6-luna','--sandbox','read-only','--json',
            '-C',str(cwd),'-c','model_reasoning_effort="low"',
            '--output-schema',str(ROOT / 'output_schema.json'),
            '--output-last-message',str(run / 'result.json'),'-']
    dump(run / 'command.json', argv)
    start = time.time()
    status = {'requested_model':'gpt-6-luna','reasoning_effort':'low',
              'start_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'prompt_sha256':hashlib.sha256((run/'prompt.txt').read_bytes()).hexdigest(),
              'isolated_cwd':str(cwd),'timeout_seconds':240,'status':'running'}
    dump(run/'status.json',status)
    print(repeat,'started',flush=True)
    with (run/'events.jsonl').open('x') as out, (run/'stderr.log').open('x') as err:
        proc = subprocess.Popen(argv,stdin=subprocess.PIPE,stdout=out,stderr=err,text=True,start_new_session=True)
        try:
            proc.communicate((run/'prompt.txt').read_text(),timeout=240)
        except subprocess.TimeoutExpired:
            osig = signal.SIGTERM
            import os
            os.killpg(proc.pid,osig)
            try:proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid,signal.SIGKILL)
                proc.wait()
            status['timed_out']=True
    status.update({'returncode':proc.returncode,'elapsed_seconds':round(time.time()-start,3),
                   'status':'output_received' if proc.returncode == 0 and (run/'result.json').is_file() else 'failed'})
    dump(run/'status.json',status)
    print(repeat,status['status'],'seconds',status['elapsed_seconds'],flush=True)
    if status['status']=='failed':
        break
