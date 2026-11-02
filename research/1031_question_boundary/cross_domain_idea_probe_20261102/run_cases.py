"""Sequential actor/tool transport per case; independent workers may run in parallel.

No scientific choices, alternative equations or edited model replies are supplied.
"""
import json
import subprocess
import sys
import time
from pathlib import Path
import harness as h

def fetch_search(rid,tool):
    run=h.ROOT/'runs'/rid;base=run/'tools'/tool['id'];result=tool['result'];raw=Path(result['output_path'])
    attempts=[]
    for attempt in range(2):
        out=subprocess.run(['curl','--silent','--show-error','--fail','--location','--max-time','40',result['url'],'--output',str(raw)],capture_output=True,text=True,timeout=45)
        attempts.append(dict(time=h.now(),attempt=attempt+1,returncode=out.returncode,stderr=out.stderr,stdout=out.stdout))
        if out.returncode==0:break
        if raw.exists():raw.rename(raw.with_name(f'partial_attempt_{attempt+1}.json'))
        if attempt==0:time.sleep(3)
    h.dump(base/'transport_attempts.json',dict(url=result['url'],attempts=attempts))
    if attempts[-1]['returncode']!=0:h.dump(base/'transport_error.json',dict(url=result['url'],attempts=attempts))
    h.finish_search(rid,tool['id'])

def run_case(rid):
    run=h.ROOT/'runs'/rid
    assert not (run/'FROZEN.json').exists()
    while h.state(run)['counters']['replies']<3:
        s=h.state(run)
        for tool in list(s['tools']):
            if tool['result']['status']=='waiting_external':fetch_search(rid,tool)
        label=h.ORDER[h.state(run)['counters']['replies']]
        if not (run/'inputs'/f'{label}.json').exists():h.make_input(rid)
        if not (run/'inputs'/f'{label}_cli_completion.json').exists():
            out=subprocess.run([sys.executable,str(h.ROOT/'cli_actor.py'),rid,label],capture_output=True,text=True,timeout=920)
            print(out.stdout,flush=True)
            if out.returncode:raise RuntimeError('CLI actor failed: '+out.stdout[-1000:]+' '+out.stderr[-1000:])
        h.ingest(rid,label)
        print(json.dumps(dict(time=h.now(),run=rid,stage=label+' completed')),flush=True)
    h.freeze(rid)
    print(json.dumps(dict(time=h.now(),run=rid,status='case frozen')),flush=True)

if __name__=='__main__':
    for rid in sys.argv[1:]:
        try:run_case(rid)
        except Exception as e:
            run=h.ROOT/'runs'/rid
            h.dump(run/'TRANSPORT_FAILURE.json',dict(time=h.now(),reason=repr(e),scope='Retained failed case; no hidden model retry or scientific output repair'))
            print(json.dumps(dict(run=rid,status='blocked',reason=repr(e))),flush=True)
