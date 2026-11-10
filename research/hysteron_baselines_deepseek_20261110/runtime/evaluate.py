"""Independent post-freeze two-duty checks with real screened source evidence."""
from common import *
import argparse,concurrent.futures

def evaluate(system):
 out=ROOT/'runs'/system;final=json.loads((out/'FINAL.json').read_text())
 Engine(system).definitions.freeze_evidence()
 frozen={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file() and p.name not in {'STATUS.json','usage.jsonl','GENERATION_FREEZE.json'}}
 dump(out/'GENERATION_FREEZE.json',{'files':frozen,'at':datetime.now(timezone.utc).isoformat()})
 e=Engine(system+'_evaluation');target=e.out/'CHECKS.json'
 if not target.exists():
  plan=e.run([{'role':'system','content':'Plan a very small prior-work overlap search for these concrete hypotheses. Use established scientific terminology. Two duties later: similar existing direction and obvious math/logical error. Return at most 4 short English queries total, with hypothesis_ids.'},{'role':'user','content':json.dumps(final,ensure_ascii=False)}],function={'name':'search_plan','description':'Targeted literature queries','parameters':{'type':'object','properties':{'queries':{'type':'array','maxItems':4,'items':{'type':'object','properties':{'query':{'type':'string'},'hypothesis_ids':{'type':'array','items':{'type':'string'}}},'required':['query','hypothesis_ids']}}},'required':['queries']}})
  dump(e.out/'SEARCH_PLAN.json',plan)
  searches=[]
  queries=[q['query'] for q in plan['queries']][:4]
  for i in range(0,len(queries),2):searches.append(e.science_call('search_sources',{'queries':queries[i:i+2]},'evaluation_'+str(i)))
  dump(e.out/'SEARCH_RESULTS.json',searches)
  sources=list(e.broker.sources.values())
  # Supply the registered readable source body, not merely a search title.
  source_packet=[{k:s.get(k) for k in ['id','title','url','date','access','text','date_evidence']} for s in sources]
  instruction='''Independently perform exactly two duties for EVERY frozen hypothesis: (1) flag a very similar pre-existing research direction, even if details differ; compare problem, mechanism and contribution using actual supplied readable sources, or mark uncertainty when coverage is insufficient; (2) check obvious arithmetic, equation, dimensional or logical mistakes, citing concrete steps. Conditional/unvalidated mechanisms can pass. Do not demand experiments, proof, implementation or guaranteed novelty. Unknown apparatus details do not alone make a hypothesis mathematically wrong. Do not rewrite or develop a new hypothesis. A plan/definition alone is not mechanism progress; describe it accurately. Use Chinese. Prior-work statuses: already_done/no_close_work_found/unclear. Coherence: no_obvious_error/obvious_error/unclear. No-close means this bounded search only. For each cited source give exact supporting quote from its text; do not cite invented sources. If no source directly supports already_done, use unclear. Historical reference date is strictly before 2024-09-12.'''
  contract={'name':'save_checks','description':'Save independent two-duty evaluation','parameters':{'type':'object','properties':{'checks':{'type':'array','items':{'type':'object','properties':{'hypothesis_id':{'type':'string'},'prior_work_status':{'type':'string','enum':['already_done','no_close_work_found','unclear']},'prior_work_reason':{'type':'string'},'sources':{'type':'array','items':{'type':'object','properties':{'source_id':{'type':'string'},'quote':{'type':'string'},'relation':{'type':'string'}},'required':['source_id','quote','relation']}},'coherence_status':{'type':'string','enum':['no_obvious_error','obvious_error','unclear']},'coherence_reason':{'type':'string'},'substantive_content':{'type':'string'}},'required':['hypothesis_id','prior_work_status','prior_work_reason','sources','coherence_status','coherence_reason','substantive_content']}}},'required':['checks']}}
  checks=e.run([{'role':'system','content':instruction},{'role':'user','content':json.dumps({'hypotheses':final,'case':brief(),'sources':source_packet,'search_status':searches},ensure_ascii=False)}],function=contract)
  assert {c['hypothesis_id'] for c in checks['checks']}=={h['id'] for h in final['hypotheses']}
  by_id={s['id']:s for s in sources}
  for c in checks['checks']:
   valid=[];rejected=[]
   for s in c['sources']:
    if s['source_id'] in by_id and s['quote'] and s['quote'] in by_id[s['source_id']]['text']:valid.append(s)
    else:rejected.append(s)
   c['sources']=valid
   if rejected:c['unsupported_citations']=rejected
   if c['prior_work_status']=='already_done' and not valid:
    c['prior_work_status']='unclear';c['evidence_validation']='No matching exact source support for already_done'
  dump(target,checks)
 for path,sha in frozen.items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==sha,path
 status=json.loads((out/'STATUS.json').read_text());status.update(status='complete',independent_evaluation=str(target),generation_unchanged=True)
 dump(out/'STATUS.json',status)
 dump(e.out/'STATUS.json',{'status':'complete','generation_unchanged':True,'checks':len(final['hypotheses'])})
 return system,'complete'

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--systems',nargs='+',default=['researchagent','virtual_lab','scientist_v2','evoscientist']);ap.add_argument('--wait',action='store_true');a=ap.parse_args()
 def ready(system):
  while a.wait:
   p=ROOT/'runs'/system/'STATUS.json'
   if p.exists() and json.loads(p.read_text()).get('status') in ['generation_complete','complete']:break
   time.sleep(3)
  return evaluate(system)
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
  for f in concurrent.futures.as_completed([pool.submit(ready,s) for s in a.systems]):print(f.result(),flush=True)
