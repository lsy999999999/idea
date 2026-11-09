"""Serve model requests over authenticated SSH; provider credential stays local."""
from pathlib import Path
import concurrent.futures
import json
import shlex
import sys
import time
import traceback
import requests
from model_adapter import complete
from server_ops import connect

ROOT=Path(__file__).resolve().parent
client=connect();s=client.open_sftp();remote=s.normalize('.')+'/ideas_replication_20261108'
if len(sys.argv)>2 and sys.argv[1]=='--attach':
    pid=int(sys.argv[2])
    command=f'while kill -0 {pid} 2>/dev/null; do sleep 1; done'
else:
    s.put(str(ROOT/'server_experiment.py'),remote+'/server_experiment.py')
    for old,new in [('results/STATUS.json','results/STATUS_attempt0.json'),('server_run.log','server_run_attempt0.log')]:
        try:s.stat(remote+'/'+new)
        except IOError:
            try:s.rename(remote+'/'+old,remote+'/'+new)
            except IOError:pass
    command='cd '+shlex.quote(remote)+' && .venv/bin/python -u server_experiment.py > server_run.log 2>&1'
_,stdout,stderr=client.exec_command(command,timeout=1500)
handled=set();start=time.time()
def answer(payload):
    if payload['kind']=='model':return complete(payload['messages'],'scientist_v2',payload.get('max_tokens',2400),payload.get('function'))
    response=requests.get('https://api.semanticscholar.org/graph/v1/paper/search',params={'query':payload['query'],'limit':5,'fields':'title,authors,venue,year,abstract,citationCount'},timeout=20)
    folder=ROOT/'runs/scientist_v2/literature';folder.mkdir(parents=True,exist_ok=True)
    (folder/f'{time.time_ns()}.json').write_text(json.dumps({'query':payload['query'],'status':response.status_code,'body':response.text},ensure_ascii=False,indent=2))
    if response.status_code!=200:return f'Semantic Scholar retrieval failed with HTTP {response.status_code}; novelty remains unresolved.'
    return json.dumps(response.json(),ensure_ascii=False)
try:
    while time.time()-start<1500:
        try:names=s.listdir(remote+'/requests')
        except IOError:names=[]
        for name in names:
            if not name.endswith('.request.json') or name in handled:continue
            if name.replace('.request.json','.answer.json') in names:
                handled.add(name)
                continue
            handled.add(name)
            with s.open(remote+'/requests/'+name) as f:payload=json.load(f)
            try:data={'result':answer(payload)}
            except Exception as e:data={'error':type(e).__name__+': '+str(e)}
            target=remote+'/requests/'+name.replace('.request.json','.answer.json')
            with s.open(target+'.tmp','w') as f:f.write(json.dumps(data,ensure_ascii=False))
            s.rename(target+'.tmp',target)
        if stdout.channel.exit_status_ready():break
        time.sleep(.4)
    print('remote_exit',stdout.channel.recv_exit_status(),flush=True)
    local=ROOT/'runs/scientist_v2/server';local.mkdir(parents=True,exist_ok=True)
    def pull(remote_dir,local_dir):
        local_dir.mkdir(parents=True,exist_ok=True)
        import stat
        for item in s.listdir_attr(remote_dir):
            if stat.S_ISDIR(item.st_mode):pull(remote_dir+'/'+item.filename,local_dir/item.filename)
            else:s.get(remote_dir+'/'+item.filename,str(local_dir/item.filename))
    pull(remote+'/results',local)
    s.get(remote+'/server_run.log',str(local/'server_run.log'))
    print((local/'STATUS.json').read_text()[:500],flush=True)
finally:client.close()
