"""Run the four authorized native systems, checkpoint outputs, continue unaffected jobs."""
from pathlib import Path
import subprocess,sys,json,time,concurrent.futures
ROOT=Path(__file__).resolve().parents[1]
systems=['researchagent','virtual_lab','scientist_v2','evoscientist']
def run(system):
 status=ROOT/'runs'/system/'STATUS.json'
 if status.exists() and json.loads(status.read_text()).get('status') in ['generation_complete','complete']:return system,'already_complete'
 cmd=[sys.executable,str(ROOT/'runtime/drive_server.py')] if system=='scientist_v2' else [sys.executable,str(ROOT/'runtime/local_system.py'),'--system',system]
 with (ROOT/(system+'.log')).open('a') as log:
  for attempt in range(3):
   r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
   if r.returncode==0:return system,'generation_complete'
   time.sleep(3)
 return system,'needs_repair'
if __name__=='__main__':
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
  for future in concurrent.futures.as_completed([pool.submit(run,s) for s in systems]):print(future.result(),flush=True)
