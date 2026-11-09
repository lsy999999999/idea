"""SSH file bridge; model credentials stay on the local computer."""
from pathlib import Path
import json,sys,time,shlex,argparse,stat
from openai import OpenAI
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/'replication_selection_20261108/execution'))
from server_ops import connect
ap=argparse.ArgumentParser();ap.add_argument('--case',required=True);ap.add_argument('--phase',default='generation');a=ap.parse_args()
ssh=connect();s=ssh.open_sftp();remote=s.normalize('.')+'/'+ROOT.name
def mkdir(path):
 try:s.mkdir(path)
 except IOError:pass
mkdir(remote);mkdir(remote+'/requests');mkdir(remote+'/cases');mkdir(remote+'/cases/'+a.case)
s.put(str(ROOT/'runtime/server_scientist.py'),remote+'/server_scientist.py')
s.put(str(ROOT/'model_config.json'),remote+'/model_config.json')
for name in ['dossier.json','measurements.csv','correction_packet.json']:s.put(str(ROOT/'cases'/a.case/name),remote+'/cases/'+a.case+'/'+name)
log=f'{a.case}_{a.phase}.log'
command='cd '+shlex.quote(remote)+' && /home/lsy/ideas_replication_20261108/.venv/bin/python -u server_scientist.py --case '+a.case+' --phase '+a.phase+' > '+log+' 2>&1'
_,stdout,stderr=ssh.exec_command(command,timeout=2400)
api=OpenAI(base_url=json.loads((ROOT/'gateway_endpoint.json').read_text())['base_url'],api_key=f'{a.case}/scientist_v2/{a.phase}',timeout=240,max_retries=0)
model=json.loads((ROOT/'model_config.json').read_text())['model']
start=time.monotonic()
try:
 while time.monotonic()-start<2300:
  names=s.listdir(remote+'/requests')
  for name in names:
   if not name.endswith('.request.json') or name.replace('.request.json','.answer.json') in names:continue
   with s.open(remote+'/requests/'+name) as f:p=json.load(f)
   if p['group']!=f'{a.case}/scientist_v2/{a.phase}':continue
   kwargs={'model':model,'messages':p['messages'],'max_tokens':p['max_tokens']}
   if p.get('function'):kwargs.update(tools=[{'type':'function','function':p['function']}],tool_choice={'type':'function','function':{'name':p['function']['name']}})
   try:
    for retry in range(3):
     try:r=api.chat.completions.create(**kwargs);break
     except Exception as e:
      if retry==2 or 'BUDGET_EXHAUSTED' in str(e):raise
      time.sleep(2)
    msg=r.choices[0].message;data={'result':json.loads(msg.tool_calls[0].function.arguments) if p.get('function') else msg.content}
   except Exception as e:data={'error':str(e)}
   target=remote+'/requests/'+name.replace('.request.json','.answer.json')
   with s.open(target+'.tmp','w') as f:f.write(json.dumps(data))
   s.rename(target+'.tmp',target)
  if stdout.channel.exit_status_ready():break
  time.sleep(.4)
 def pull(src,dst):
  dst.mkdir(parents=True,exist_ok=True)
  for item in s.listdir_attr(src):
   if stat.S_ISDIR(item.st_mode):pull(src+'/'+item.filename,dst/item.filename)
   else:s.get(src+'/'+item.filename,str(dst/item.filename))
 local=ROOT/'runs'/a.case/'scientist_v2'/a.phase
 pull(remote+'/runs/'+a.case+'/scientist_v2/'+a.phase,local)
 s.get(remote+'/'+log,str(local/'server.log'))
 print((local/'STATUS.json').read_text(),flush=True)
finally:ssh.close()
