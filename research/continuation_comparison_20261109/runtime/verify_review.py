"""Bounded live replay of the previously blocked review; never resumes a frozen run."""
import argparse,json,shutil,subprocess,sys,time,traceback
from pathlib import Path
from openai import OpenAI
import run_ours as runner
from learning_support import REVIEW_PROTOCOL,audit_review

def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--execute',action='store_true');p.add_argument('--name',default='review_verification');a=p.parse_args()
 if not a.execute:print('Prepared review-only verification; no model calls');return
 if not a.name.replace('_','').isalnum():raise ValueError('Use letters and underscores for the verification name')
 root=runner.ROOT;out=root/a.name;out.mkdir(exist_ok=True)
 if (out/'STATUS.json').exists():raise ValueError('Verification already completed; preserve it and use a new root')
 endpoint=root/'gateway_endpoint.json'
 if endpoint.exists():raise ValueError('Existing gateway endpoint; do not start a second writer')
 log=(out/'gateway.log').open('w');gateway=subprocess.Popen([sys.executable,str(root/'runtime/model_gateway.py')],stdout=log,stderr=subprocess.STDOUT)
 try:
  for _ in range(100):
   if endpoint.exists():break
   if gateway.poll() is not None:raise RuntimeError('Gateway stopped')
   time.sleep(.1)
  cfg=runner.read(root/'model_config.json')
  api=OpenAI(base_url=runner.read(endpoint)['base_url'],api_key='optical/'+a.name+'/generation',max_retries=0,timeout=240)
  adapter=runner.StageAdapter(root,'optical','generation',cfg,api=api)
  adapter.run=runner.PROJECT/'runs'/a.name
  target=adapter.run/'internal_review/inputs.json';target.parent.mkdir(parents=True,exist_ok=True)
  if target.exists() and target.read_bytes()!=a.source.read_bytes():raise ValueError('Review source changed')
  shutil.copy2(a.source,target)
  path,result=adapter(adapter.run,'04_internal_review','internal_reasoning_reviewer',REVIEW_PROTOCOL,[target],cfg['model'],cfg.get('reasoning_effort'),240)
  report=audit_review(result,runner.read(target));runner.write(out/'report.json',report)
  runner.write(out/'STATUS.json',{'status':'complete','scope':'Actual native internal review of unchanged historical material, using repaired transport. Not a new full research run.','result_path':str(path),'findings':len(report['findings'])})
 except BaseException as exc:
  runner.write(out/'STATUS.json',{'status':'failed','error':str(exc),'traceback':traceback.format_exc()});raise
 finally:
  gateway.terminate();gateway.wait(timeout=10);log.close()
  if endpoint.exists() and runner.read(endpoint).get('pid')==gateway.pid:endpoint.unlink()

if __name__=='__main__':main()
