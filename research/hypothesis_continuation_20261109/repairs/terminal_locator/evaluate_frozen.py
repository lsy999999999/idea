"""Post-freeze application of the existing two-duty claim-centric checker."""
from pathlib import Path
import json,hashlib,subprocess,sys,time,traceback
import run_ours as m
from novelty_scope import evaluate_scope
from idea_check import CHECKER_PROMPT,validate_checks
ROOT=m.ROOT
GEN=m.PROJECT/'runs/hypothesis_metadata_optical_generation'
class FinalAdapter(m.StageAdapter):
 def normalize(self,result,bindings,store,context=None):
  out=super().normalize(result,bindings,store,context)
  def resolve(value):
   if isinstance(value,list):return [resolve(v) for v in value]
   if not isinstance(value,dict):return value
   value={k:resolve(v) for k,v in value.items()}
   locator=value.get('snapshot_path')
   if isinstance(locator,str) and not Path(locator).is_file():
    ref=store.resolve(locator);paths=[p for p in store.documents[ref]['paths'] if Path(p).is_file()]
    if len(paths)==1:value['snapshot_path']=paths[0]
   return value
  out=resolve(out)
  for check in out.get('checks',[]):
   sources={row['source_id']:row for row in check.get('prior_work',{}).get('sources',[])}
   for source in sources.values():
    source.setdefault('publication_date',None)
    path=source.get('snapshot_path')
    if path and Path(path).is_file() and source['publication_date'] is None:
     try:record=m.read(Path(path))
     except (ValueError,UnicodeError):continue
     day=record.get('date') if isinstance(record,dict) else None
     if isinstance(day,str) and len(day)==10 and record.get('date_evidence'):
      source['publication_date']={'earliest':day,'latest':day,'url':record.get('url',source['url']),'snapshot_path':path,'quote':day}
   novelty=check.get('novelty',{});claims=novelty.get('claims',[])
   rows={c['claim_id']:[] for c in claims}
   for comparison in novelty.get('comparisons',[]):
    for row in comparison.get('claim_relations',[]):
     if row.get('claim_id') in rows:rows[row['claim_id']].append((comparison['source_id'],row['relation']))
   idea=next((i for i in self.ideas if i['id']==check.get('idea_id')),None)
   if idea is not None and claims:
    completed={s.get('facet') for s in out.get('searches',[]) if s.get('status')=='completed' and idea['id'] in s.get('idea_ids',[])}=={'problem','mechanism','contribution'}
    coverage,overall,assessment=evaluate_scope(idea,sources,rows,completed,m.PROJECT)
    for claim in claims:claim['coverage']=coverage[claim['claim_id']]
    novelty.update(overall_status=overall,assessment=assessment)
    if overall=='UNCLEAR':novelty['recommended_action']='TARGETED_SEARCH'
  return out
 def validate(self,result,sid,role,context,inputs):
  super().validate(result,sid,role,context,inputs)
  validate_checks(result,self.ideas,require_claims=True)

def main():
 frozen=m.read(GEN/'GENERATION_FREEZE.json')
 for path,digest in frozen['files'].items():
  if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=digest:raise ValueError('Generation changed before final check')
 cfg=m.read(ROOT/'model_config.json');cfg['budgets']['evaluation']={'input_tokens':2000000,'output_tokens':150000,'calls':100}
 m.write(ROOT/'model_config.json',cfg)
 if (ROOT/'gateway_endpoint.json').exists():raise ValueError('Existing gateway; wait for generation runner to close')
 log=(ROOT/'evaluation_gateway.log').open('w');gateway=subprocess.Popen([sys.executable,str(ROOT/'runtime/model_gateway.py')],stdout=log,stderr=subprocess.STDOUT)
 try:
  for _ in range(100):
   if (ROOT/'gateway_endpoint.json').exists():break
   if gateway.poll() is not None:raise RuntimeError('Gateway startup failed')
   time.sleep(.1)
  a=FinalAdapter(ROOT,'optical','evaluation',cfg);a.run=m.PROJECT/'evaluations/hypothesis_metadata_final';a.run.mkdir(parents=True,exist_ok=True)
  context_path=a.run/'EVALUATION_CONTEXT.json'
  context={'mode':'historical','reference_date':{'earliest':'2026-08-12','latest':'2026-08-12','evidence_kind':'task_configuration','snapshot_path':str(context_path),'quote':'2026-08-12'},'reference_reason':'Registered case knowledge boundary: independently dated knowledge strictly before 2026-08-12; raw measurement exception; originating explanations were excluded during generation.','source_papers':[]}
  m.write(context_path,context)
  a.ideas=[{**idea,'evaluation_context':context} for idea in m.read(GEN/'ideas.json')['ideas']]
  path=a.run/'ideas.json';m.write(path,{'ideas':a.ideas,'frozen_generation':str(GEN/'ideas.json'),'controller_metadata_only':True})
  if a.ideas:
   prompt=CHECKER_PROMPT+'\nThe controller resolves registered snapshot document IDs and computes deterministic coverage/date aggregation from your own comparisons. Do not feed any evaluation back to generation. Use actual screened search/read tools; record insufficient access as unresolved. Cite existing source/tool files for snapshots. Chinese readable result.'
   result_path,result=a(a.run,'terminal_check','idea_check_agent',prompt,[path,m.lab.POLICY,context_path],cfg['model'],cfg.get('reasoning_effort'),240)
  else:result_path=None;result={'checks':[],'searches':[],'reason':'No generated candidates'}
  m.write(a.out/'result.json',{'source':str(result_path),'result':result,'generation_frozen':True})
  for path,digest in frozen['files'].items():
   if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=digest:raise ValueError('Evaluator altered frozen generation')
  for path,digest in frozen['memory_files'].items():
   if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=digest:raise ValueError('Evaluator altered research memory')
  m.write(a.out/'STATUS.json',{'status':'complete','schema':'claim-centric-v2','generation_and_memory_unchanged':True,'researcher_calls_after_evaluation':0})
  print('Final two-duty check complete',flush=True)
 finally:
  gateway.terminate();gateway.wait(timeout=10);log.close()
  endpoint=ROOT/'gateway_endpoint.json'
  if endpoint.exists() and m.read(endpoint).get('pid')==gateway.pid:endpoint.unlink()
if __name__=='__main__':
 try:main()
 except BaseException:
  print(traceback.format_exc(),flush=True);raise
