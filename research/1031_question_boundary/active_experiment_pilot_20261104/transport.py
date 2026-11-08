"""Frozen inference transport, shared artifact helpers; no research tools inside CLI."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
ROOT=Path(__file__).resolve().parent
PREVIOUS=ROOT.parent/'tool_use_pilot_20261103'
STERILE=Path('/private/tmp/idea-active-experiment-20261104-inference')
CLI='/opt/homebrew/bin/codex'
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x') as f:f.write(v if isinstance(v,str) else json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False))
def cached(p,fn):
    if Path(p).exists():return read(p)
    value=fn();write(p,value);return value
def verify():
    frozen=read(ROOT/'FROZEN.json')
    for p,h in frozen['files'].items():assert sha(ROOT/p)==h,p
    for p,h in frozen['previous_files'].items():assert sha(PREVIOUS/p)==h,p
    assert sha(STERILE/'AGENTS.md')==frozen['sterile_sha256']

def infer(index,arm,bundle):
    verify();assert 1<=index<=4
    dest=ROOT/'calls'/f'{index:02d}_{arm}'
    prompt='Controlled scientific modeling. Use only the JSON evidence and prior within-condition tool outputs. Return one JSON object. Do not use native tools, files, memory, network, shell or delegation.\n'+json.dumps(bundle,ensure_ascii=False)
    if dest.exists():
        assert read(dest/'input.json')==bundle
        if (dest/'reply.json').exists():return read(dest/'reply.json')
    else:dest.mkdir(parents=True);write(dest/'input.json',bundle);write(dest/'prompt.txt',prompt)
    for attempt in range(2):
        done=dest/f'completion_{attempt}.json'
        if done.exists():
            if read(done)['returncode']==0:raise RuntimeError('Successful raw output requires audit; no new scientific retry')
            continue
        cmd=[CLI,'exec','--ephemeral','--skip-git-repo-check','--model','gpt-6-luna','-c','model_reasoning_effort="low"','--sandbox','read-only','--color','never','--json','--output-schema',str(ROOT/(arm+'_schema.json')),'--output-last-message',str(dest/f'output_{attempt}.txt'),'-C',str(STERILE),'-']
        write(dest/f'command_{attempt}.json',cmd);start=time.monotonic()
        with (dest/f'events_{attempt}.jsonl').open('x') as out,(dest/f'stderr_{attempt}.txt').open('x') as err:
            try:rc=subprocess.run(cmd,input=prompt,text=True,stdout=out,stderr=err,timeout=600).returncode
            except subprocess.TimeoutExpired:rc=124
        usage={};violations=[]
        for line in (dest/f'events_{attempt}.jsonl').read_text().splitlines():
            try:event=json.loads(line)
            except json.JSONDecodeError:continue
            if event.get('type')=='turn.completed':usage=event.get('usage',{})
            if event.get('item',{}).get('type') in ['command_execution','mcp_tool_call','web_search','file_change']:violations.append(event['item']['type'])
        write(done,dict(time=now(),returncode=rc,seconds=time.monotonic()-start,usage=usage,tool_violations=violations,requested_model='gpt-6-luna',requested_reasoning='low',backend_weights_verified=False))
        if rc:raise RuntimeError('Transport failed; preserve logs and resume identical input only')
        if violations:raise RuntimeError('Prohibited native tool use')
        raw=(dest/f'output_{attempt}.txt').read_text().strip();raw=re.sub(r'^```(?:json)?\s*|\s*```$','',raw)
        reply=json.loads(raw);write(dest/'reply.json',reply);write(dest/'SEALED.json',dict(time=now(),input_sha256=sha(dest/'input.json'),reply_sha256=sha(dest/'reply.json')))
        print(json.dumps(dict(call=index,arm=arm,usage=usage)),flush=True);return reply
    raise RuntimeError('Transport retries exhausted')
