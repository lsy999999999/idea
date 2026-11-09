"""Small live tool/submit/save check with independent numerical assertions."""
from pathlib import Path
import json,subprocess,sys,time,traceback
from openai import OpenAI
import run_ours as r

def main():
 root=r.ROOT;out=root/'tool_verification';out.mkdir(exist_ok=True)
 if (out/'STATUS.json').exists():raise ValueError('Already verified; use a fresh root')
 endpoint=root/'gateway_endpoint.json'
 if endpoint.exists():raise ValueError('Existing gateway')
 log=(out/'gateway.log').open('w');gateway=subprocess.Popen([sys.executable,str(root/'runtime/model_gateway.py')],stdout=log,stderr=subprocess.STDOUT)
 try:
  for _ in range(100):
   if endpoint.exists():break
   if gateway.poll() is not None:raise RuntimeError('Gateway stopped')
   time.sleep(.1)
  cfg=r.read(root/'model_config.json');api=OpenAI(base_url=r.read(endpoint)['base_url'],api_key='optical/interface_tools/generation',max_retries=0,timeout=240)
  adapter=r.StageAdapter(root,'optical','generation',cfg,api=api);adapter.run=r.PROJECT/'runs/tool_verification'
  task=out/'task.json';r.write(task,{'purpose':'Interface verification, not scientific discovery','dataset':'measurements','measurements':'Use DOP and S1/S2/S3 from actual CSV; report full and selected row counts.'})
  path,result=adapter(adapter.run,'verify_tools','interface_tester',
   'Test the transport. First use read_documents to read BOTH supplied inputs in one batch (even if inlined, this checks batching). Then use analyze_csv on scan=mean_phase to compute mean(S1**2+S2**2+S3**2) and mean(DOP). Submit a concise result with summary string, artifacts/evidence/claims/limitations/next_actions arrays and metrics {total_rows,selected_rows,norm_squared_mean,dop_mean}. Cite tool record paths in evidence. No search needed.',
   [task,root/'cases/optical/source_manifest.json'],cfg['model'],cfg.get('reasoning_effort'),240)
  m=result['metrics'];assert m['total_rows']==302 and m['selected_rows']==200
  assert abs(m['norm_squared_mean']-.9999956376501004)<1e-10 and abs(m['dop_mean']-.79511738465)<1e-10
  records=[r.read(p) for p in path.parent.glob('tools/*.json')];assert any(x['name']=='read_documents' and len(x['result']['documents'])==2 for x in records)
  assert any(x['name']=='analyze_csv' and x['result']['status']=='executed' for x in records)
  r.write(out/'STATUS.json',{'status':'complete','result':str(path),'metrics':m,'checked':['batched exact document reads','full CSV execution','independent numerical agreement','validated submit','real artifact file saved']})
 except BaseException as exc:r.write(out/'STATUS.json',{'status':'failed','error':str(exc),'traceback':traceback.format_exc()});raise
 finally:
  gateway.terminate();gateway.wait(timeout=10);log.close()
  if endpoint.exists() and r.read(endpoint).get('pid')==gateway.pid:endpoint.unlink()

if __name__=='__main__':main()
