from common import *
if __name__=='__main__':
 import argparse
 ap=argparse.ArgumentParser();ap.add_argument('--audit',action='store_true');a=ap.parse_args()
 e=Engine('shared_prior_work_evaluation')
 queries=['interacting mechanical hysterons memory','hysteretic networks transition graphs return point memory']
 result=e.science_call('search_sources',{'queries':queries},'broad_directions')
 dump(e.out/'BROAD_SEARCH.json',result)
 print('Broad dated sources',len(e.broker.sources),flush=True)
 if a.audit:
  systems=['researchagent','virtual_lab','scientist_v2','evoscientist']
  while not all((ROOT/'runs'/s/'FINAL.json').exists() for s in systems):time.sleep(3)
  frozen={s:json.loads((ROOT/'runs'/s/'FINAL.json').read_text()) for s in systems}
  # Relevant broad work; retain all raw retrieval results separately.
  sources=[s for s in e.broker.sources.values() if any(t in s['title'].lower() for t in ['hysteron','preisach','crumpled'])]
  instruction='''Audit prior-work similarity at the level of scientific research directions for every candidate below. Some earlier checkers rejected overlap merely because a source uses a different apparatus, rotor count, or not the exact hard-stop geometry. That criterion is too narrow. A very similar existing PROBLEM + CENTRAL MECHANISM or CONTRIBUTION is already_done even when implementation and details differ. Generic neighboring keywords alone are not enough. Identify exactly which part is covered and which specific relation remains unresolved; distinguish routine torque balance/curve fitting/parameter normalization/identifiability plans from a newly developed explanation. Do not demand scientific validation or proofs. Give already_done, no_close_work_found (bounded search only), or unclear; when sources cannot assess the actual mechanism use unclear. Compare both close matches and material differences. Cite actual source IDs and exact supporting text. No original study and no new generation. Chinese output. One compact entry for each system/hypothesis ID, retain all candidates.'''
  contract={'name':'save_broad_audit','description':'Broad scientific-direction overlap check','parameters':{'type':'object','properties':{'checks':{'type':'array','items':{'type':'object','properties':{'system':{'type':'string'},'hypothesis_id':{'type':'string'},'prior_work_status':{'type':'string','enum':['already_done','no_close_work_found','unclear']},'reason':{'type':'string'},'sources':{'type':'array','items':{'type':'object','properties':{'source_id':{'type':'string'},'quote':{'type':'string'},'relation':{'type':'string'}},'required':['source_id','quote','relation']}}},'required':['system','hypothesis_id','prior_work_status','reason','sources']}}},'required':['checks']}}
  p=e.out/'BROAD_SCOPE_AUDIT.json'
  if not p.exists():
   value=e.run([{'role':'system','content':instruction},{'role':'user','content':json.dumps({'frozen_candidates':frozen,'sources':[{k:s.get(k) for k in ['id','title','url','date','date_evidence','publication_dates','access','text']} for s in sources]},ensure_ascii=False)}],function=contract)
   assert {(c['system'],c['hypothesis_id']) for c in value['checks']}=={(s,h['id']) for s,f in frozen.items() for h in f['hypotheses']}
   by_id={s['id']:s for s in sources}
   for c in value['checks']:
    valid=[x for x in c['sources'] if x['source_id'] in by_id and x['quote'] and x['quote'] in by_id[x['source_id']]['text']]
    if len(valid)!=len(c['sources']):c['citation_validation_note']='Unsupported quotes excluded'
    c['sources']=valid
    if c['prior_work_status']=='already_done' and not valid:c['prior_work_status']='unclear';c['citation_validation_note']='No exact supporting quotation for already_done'
   dump(p,value)
  dump(e.out/'STATUS.json',{'status':'complete','scope':'post-generation broad direction overlap audit','calls':1})
  print('Broad scope audit complete',flush=True)
