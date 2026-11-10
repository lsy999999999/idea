from common import *
import shlex,stat,traceback,fcntl
sys.path.insert(0,str(UP/'execution'))
from server_ops import connect

def main():
 folder=ROOT/'runs/scientist_v2';folder.mkdir(parents=True,exist_ok=True)
 run_lock=(folder/'.run.lock').open('a');fcntl.flock(run_lock,fcntl.LOCK_EX)
 if (folder/'STATUS.json').exists() and json.loads((folder/'STATUS.json').read_text()).get('status') in ['generation_complete','complete']:return
 e=Engine('scientist_v2');dump(e.out/'STATUS.json',{'status':'running','host':'priority_server'})
 ssh=connect();s=ssh.open_sftp();remote=s.normalize('.')+'/'+ROOT.name
 def mkdir(p):
  try:s.mkdir(p)
  except IOError:pass
 mkdir(remote);mkdir(remote+'/requests')
 s.put(str(ROOT/'runtime/server_scientist.py'),remote+'/server_scientist.py')
 local=ROOT/'actor_brief.json';dump(local,brief());s.put(str(local),remote+'/dossier.json')
 s.put(str(ROOT/'cases/hysteron/measurements.csv'),remote+'/measurements.csv')
 cmd='cd '+shlex.quote(remote)+' && /home/lsy/ideas_replication_20261108/.venv/bin/python -u server_scientist.py > server.log 2>&1'
 _,stdout,stderr=ssh.exec_command(cmd,timeout=14400)
 print('SERVER_STARTED',remote,flush=True)
 try:
  while True:
   names=s.listdir(remote+'/requests')
   for name in names:
    if not name.endswith('.request.json') or name.replace('.request.json','.answer.json') in names:continue
    with s.open(remote+'/requests/'+name) as f:p=json.load(f)
    dump(e.out/'bridge'/name,p)
    try:
     if p.get('tool'):
      t=p['tool'];result=e.science_call(t['name'],t['arguments'],name)
     else:
      result=e.run(p['messages'],function=p.get('function'))
      if not p.get('function'):result=result.choices[0].message.content
     data={'result':result}
    except Exception as ex:data={'error':str(ex)}
    dump(e.out/'bridge'/name.replace('.request.json','.answer.json'),data)
    target=remote+'/requests/'+name.replace('.request.json','.answer.json')
    with s.open(target+'.tmp','w') as f:f.write(json.dumps(data,ensure_ascii=False))
    s.rename(target+'.tmp',target)
   if stdout.channel.exit_status_ready():break
   time.sleep(.5)
  def pull(src,dst):
   dst.mkdir(parents=True,exist_ok=True)
   for item in s.listdir_attr(src):
    if stat.S_ISDIR(item.st_mode):pull(src+'/'+item.filename,dst/item.filename)
    else:s.get(src+'/'+item.filename,str(dst/item.filename))
  pull(remote+'/runs/scientist_v2',e.out/'server')
  s.get(remote+'/server.log',str(e.out/'server.log'))
  status=json.loads((e.out/'server/STATUS.json').read_text())
  if status['status']!='native_complete':raise RuntimeError(status)
  result=json.loads((e.out/'server/native_result.json').read_text());dump(e.out/'native_result.json',result)
  final=finalize(e,result);dump(e.out/'STATUS.json',{'status':'generation_complete','host':'priority_server','hypotheses':len(final['hypotheses']),'native_status':status})
 finally:ssh.close()

if __name__=='__main__':
 try:main()
 except Exception as e:
  dump(ROOT/'runs/scientist_v2/STATUS.json',{'status':'failed','error':str(e),'traceback':traceback.format_exc()});raise
