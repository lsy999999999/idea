"""Behavioral checks for hypothesis development, expertise and isolated fact disclosure."""
import hashlib,json,shutil,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import run_ours as runner
from definition_service import DefinitionService
from hypothesis_rounds import run_rounds,validate_research_turn
from learning_support import LearningServices
from request_routing import service_request
from hypothesis_cycle import context
from research_context import ContextStore
from research_tools import ResearchTools


def write(p,obj):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,ensure_ascii=False))

class DisclosureTests(unittest.TestCase):
 def service(self,root,judge):
  source=root/'controller_only/original.txt';source.parent.mkdir();source.write_text('The sensor reports a 0–1 fraction. SECRET target mechanism.')
  registry=source.parent/'registry.json';write(registry,{'documents':[{'id':'O1','path':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest()}]})
  return DefinitionService(registry,source.parent/'audit',root/'public',judge)
 def test_neutral_facts_released_and_original_remains_inaccessible(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);calls=[]
   def judge(role,prompt,data):
    calls.append(role)
    if role=='definition_reader':return {'status':'released','facts':[{'statement':'The scale is 0–1.','source_id':'O1','quote':'The sensor reports a 0–1 fraction.'}]}
    return {'question_is_neutral':True,'answer_is_neutral':True,'supported':True}
   service=self.service(root,judge);store=ContextStore(root/'documents')
   tool=ResearchTools(store,root/'stage',{},definitions=service)
   reply=tool.call('request_case_definition',{'question':'What is the scale?'},'one')
   self.assertEqual(reply['status'],'released');self.assertNotIn('SECRET',json.dumps(reply))
   tool.call('request_case_definition',{'question':'What is the scale?'},'two')
   self.assertEqual(len(calls),2)
   self.assertTrue(all('SECRET' not in doc['text'] for doc in store.documents.values()))
   with self.assertRaises(ValueError):store.read(str(root/'controller_only/original.txt'))
   audit=json.loads(next((root/'controller_only/audit').glob('*.json')).read_text())
   self.assertEqual(audit['proposal']['facts'][0]['source_id'],'O1')
 def test_question_and_answer_both_screened(self):
  for field in ['question_is_neutral','answer_is_neutral','supported']:
   with self.subTest(field=field),tempfile.TemporaryDirectory() as td:
    def judge(role,prompt,data):
     if role=='definition_reader':return {'status':'released','facts':[{'statement':'SECRET target mechanism.','source_id':'O1','quote':'SECRET target mechanism.'}]}
     return {**dict.fromkeys(['question_is_neutral','answer_is_neutral','supported'],True),field:False}
    reply=self.service(Path(td),judge).request('A mixed question')
    self.assertEqual(reply['status'],'blocked');self.assertEqual(reply['facts'],[])
 def test_bad_quote_and_modified_source_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td)
   svc=self.service(root,lambda *a:{'status':'released','facts':[{'statement':'invented','source_id':'O1','quote':'not in the source'}]})
   with self.assertRaisesRegex(ValueError,'evidence'):svc.request('scale')
   self.assertTrue(list((root/'controller_only/audit').glob('*.json')))
   (root/'controller_only/original.txt').write_text('modified')
   with self.assertRaisesRegex(ValueError,'changed'):svc.request('scale')
 def test_frozen_disclosure_basis_detects_mutation(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);svc=self.service(root,lambda *a:{'status':'unknown','facts':[]})
   svc.request('Order?');frozen=svc.freeze_evidence()
   self.assertEqual(frozen,svc.freeze_evidence())
   (root/'controller_only/original.txt').write_text('Changed evidence')
   with self.assertRaisesRegex(ValueError,'Frozen definition evidence changed'):svc.freeze_evidence()
 def test_unrecorded_fact_is_unknown(self):
  with tempfile.TemporaryDirectory() as td:
   svc=self.service(Path(td),lambda *a:{'status':'unknown','facts':[]})
   self.assertEqual(svc.request('Which averaging order?')['status'],'unknown')
 def test_request_dispatch_does_not_start_literature_for_case_facts(self):
  req,routes=service_request({'learning_request':{'needed':False,'case_questions':['What is S?']}})
  self.assertTrue(req['needed']);self.assertFalse(routes['knowledge_requested'])
 def test_public_release_tampering_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   svc=self.service(Path(td),lambda *a:{'status':'unknown','facts':[]});svc.request('Q')
   next(svc.public.glob('*.json')).write_text('{}')
   with self.assertRaisesRegex(ValueError,'modified'):svc.request('Q')

class LearningTests(unittest.TestCase):
 def test_irrelevant_sources_trigger_reformulated_search(self):
  with tempfile.TemporaryDirectory() as td:
   calls=[]
   class Broker:
    sources={}
    def search(self,request,sid):
     calls.append(request['queries']);good=len(calls)==2
     return {'sources':[{'id':'K'+str(len(calls)),'text':'Weighted sum definition.' if good else 'Unrelated absorption.'}]}
   def assess(request,sources,previous):
    good=sources[0]['id']=='K2'
    return {'assessments':[{'source_id':sources[0]['id'],'relation':'method' if good else 'irrelevant','reason':'Addresses the requested operation' if good else 'Wrong phenomenon','quote':sources[0]['text']}],
            'revised_queries':['weighted vector mixture definition']}
   service=LearningServices(Path(td),assess=assess);service.knowledge=Broker()
   p=service.reply('s',{'learning_request':{'needed':True,'queries':['initial terms'],'gap':'weighted average'}})
   result=json.loads(p.read_text())
   self.assertEqual(len(calls),2);self.assertNotEqual(calls[0],calls[1])
   self.assertEqual(result['knowledge_status'],'relevant_sources_returned')
   self.assertEqual(len(result['sources']),2) # Preserve irrelevant evidence and assessments too.
   self.assertEqual(service.reply('s',{'learning_request':{'needed':True,'queries':['initial terms'],'gap':'weighted average'}}),p)
   self.assertEqual(len(calls),2)
 def test_definition_only_reply_reaches_researcher(self):
  with tempfile.TemporaryDirectory() as td:
   definitions=SimpleNamespace(request=lambda q:{'question':q,'status':'released','facts':[{'statement':'0–1'}]})
   svc=LearningServices(Path(td),definitions=definitions)
   with patch.object(svc.knowledge,'search',side_effect=AssertionError('unexpected search')):
    p=svc.reply('s',{'learning_request':{'needed':False,'case_questions':['Scale?']}})
   self.assertEqual(json.loads(p.read_text())['case_facts'][0]['status'],'released')

class SchedulingTests(unittest.TestCase):
 def test_consultation_is_temporary_join_persists_and_resume_is_deterministic(self):
  for mode in ['consult','join']:
   with self.subTest(mode=mode),tempfile.TemporaryDirectory() as td:
    root=Path(td);seen=[];enlisted=[]
    def call(sid,owner,prompt,packet,outputs):
     seen.append((owner,packet));i=int(sid.rsplit('_',1)[1]);result={
       'development_step':{'work':'Derive a conditional consequence.'},
       'next_research_move':{'action':'consult' if i==0 else 'develop','operation':'derive','focus':'specific coupling','reason':'advance relation'}}
     if i==0:result['expertise_request']={'domain':'dynamics','relation':'coupled response','task':'derive stability consequence','mode':mode}
     if packet['progress_comparison']:result['progress_review']={**{k:packet['progress_comparison'][k] for k in ['before_stage','after_stage']},'kind':'clarification','reason':'Same relation; assumptions clarified.'}
     p=root/'outputs'/(sid+'.json');write(p,result);return p,result
    run_rounds(root,[('a','optics'),('b','optics')],[],call,lambda *a:{'outputs':[],'history':[]},lambda *a:enlisted.append(a),rounds=4)
    self.assertEqual(len(enlisted),1);self.assertTrue(seen[1][0].startswith('expert_'))
    self.assertEqual(len(seen[2][1]['active_researchers']),3 if mode=='join' else 2)
    events=(root/'research_rounds/events.json').read_bytes();seen.clear()
    run_rounds(root,[('a','optics'),('b','optics')],[],call,lambda *a:{'outputs':[],'history':[]},lambda *a:None,rounds=4)
    self.assertEqual(events,(root/'research_rounds/events.json').read_bytes())
 def test_single_researcher_and_finish(self):
  with tempfile.TemporaryDirectory() as td:
   seen=[]
   def call(sid,owner,prompt,packet,outputs):
    seen.append(owner);p=Path(td)/'result.json';r={'development_step':{'work':'Specific unresolved obstacle'},'next_research_move':{'action':'finish','operation':'hold','focus':'relation','reason':'No useful next move'}};write(p,r);return p,r
   run_rounds(td,[('a','same field')],[],call,lambda *a:{'outputs':[],'history':[]},lambda *a:None,rounds=5)
   self.assertEqual(seen,['a'])
 def test_semantic_pair_cannot_be_fabricated(self):
  with self.assertRaisesRegex(ValueError,'actual stage pair'):
   validate_research_turn({'development_step':{'work':'work'},'next_research_move':{'action':'develop','operation':'derive','focus':'f','reason':'r'},'progress_review':{'before_stage':'invented','after_stage':'b'}},
      {'active_researchers':['a'],'progress_comparison':{'before_stage':'a','after_stage':'b'}})
 def test_stagnation_uses_peer_comparison_not_authors_labels(self):
  old=[{'step':{'outcome':{'kind':'relation'}}}]*2
  sources={str(i):json.dumps({'progress_review':{'kind':'repetition','reason':'Same conditional relation','before_stage':str(i),'after_stage':str(i+1)}}) for i in range(2)}
  self.assertTrue(context(sources,old)['repeated_no_change'])
  self.assertFalse(context({},[{'step':{'outcome':{'kind':'uncertain'}}}]*2)['repeated_no_change'])

class EndToEndTests(unittest.TestCase):
 def test_full_controller_develops_recruits_freezes_and_resumes_without_new_calls(self):
  for count in [1,2,3]:
   with self.subTest(initial_researchers=count),tempfile.TemporaryDirectory() as td:
    root=Path(td);labdir=root/'lab';(labdir/'scenarios').mkdir(parents=True)
    (labdir/'scenarios/synthetic.md').write_text('Synthetic fixture: initial observations, no prior answers.')
    (labdir/'PLAN_SOURCE.md').write_text('test plan')
    docs=[]
    for i,kind in enumerate(['original_study','review']):
     p=root/f'source{i}.txt';p.write_text(f'Fixture source relation {i}');docs.append({'id':str(i),'local_path':str(p),'url':f'https://example.org/{i}','title':kind,'source_kind':kind,'content_access':'excerpt','domain_relation':'direct','relevance_reason':'Fixture','supporting_quote':p.read_text()})
    calls=[];interrupt={'pending':True}
    def stage(run,sid,role,prompt,inputs,*args):
     if sid=='09_develop_002' and interrupt['pending']:
      interrupt['pending']=False
      raise InterruptedError('Simulated interruption after recruitment')
     if sid=='07_check':raise runner.GenerationFrozen()
     calls.append(sid);r={'summary':'Fixture research output','artifacts':[],'evidence':[],'claims':[],'limitations':[],'next_actions':[],'memory_notes':[],'memory_use':[]}
     if sid=='01_materials':r.update(materials=[{'id':'m'}],sources=docs)
     elif sid=='04_internal_review':r['findings']=[]
     elif sid=='06_candidates':
      cards=json.loads((run/'candidate_history.json').read_text())['current_hypotheses'];r.update(ideas=[{'id':'I1','title':'Fixture coupling hypothesis','idea':'A conditionally changes B through the proposed coupling.'}],preserved_branches=[{'ref':c['ref'],'reason':'Retained'} for c in cards])
     else:
      c=json.loads(next(p for p in inputs if p.parent==run/'researcher_context').read_text());cy=c['development_cycle']
      r['development_step']={'focus':{'source':next(iter(cy['sources'])),'quote':None},'gap':'Mechanism relation','action':'derive','reason':'Develop consequence','expected_change':'conditional relation',
        'uptake':[{'source':p,'quote':None,'effect':'unresolved','reason':'Specific unresolved relation','consequence':None} for p in dict.fromkeys(cy['peer_sources']+cy['required_service_uptake'])],
        'outcome':{'kind':'relation','statement':'Fixture conditional consequence','remaining_gap':'Unresolved'},'work':'Fixture derivation of a conditional relation.'}
      r.update(hypothesis_updates=[],dependency_responses=[],learning_request={'needed':False})
      if sid.startswith(('02_initial_','09_onboard_')):r['initial_question']='Fixture initial question'
      else:
       q=c['question_state']['self'];r.update(personal_question_update={'base':q['ref'],'action':'retain','question':q['question'],'reason':'Continue relation','influenced_by':[]},shared_question_update=None)
      if sid.startswith('05_return_'):r['verification_responses']=[]
      if sid.startswith('09_develop_') and '_learn_' not in sid:
       packet=json.loads(next(p for p in inputs if p.parent==run/'research_rounds/inputs').read_text())
       i=int(sid.rsplit('_',1)[1]);r['next_research_move']={'action':'consult' if i==0 else 'develop','operation':'derive','focus':'Fixture relation','reason':'Develop coupling'}
       own=c['hypothesis_state']['self']
       r['hypothesis_updates']=[{'key':'coupling','base_version':own[0]['ref']['version'] if own else 0,
        'assumption':f'Fixture conditional coupling, development {i}', 'motivation':'Fixture observations',
        'conceptual_move':'Construct a coupling relation','implications':[f'Conditional consequence {i}'],
        'open_questions':['Which coupling regime?'],'status':'developing','reason':'Extend the relation',
        'influenced_by':[], 'depends_on':[]}]
       if i==0:
        r['expertise_request']={'domain':'dynamics','relation':'coupled state','task':'derive implication','mode':'join'}
        r['learning_request']={'needed':False,'case_questions':['What is the scale?']}
       if packet['progress_comparison']:r['progress_review']={**{k:packet['progress_comparison'][k] for k in ['before_stage','after_stage']},'kind':'clarification','reason':'Same relation; need further derivation'}
      elif sid.startswith('09_develop_') and '_learn_' in sid:
       r['source_use']=[]
       r['next_research_move']={'action':'consult','operation':'derive','focus':'Post-learning relation','reason':'Reviewed the definition; request specific expertise'}
       r['expertise_request']={'domain':'dynamics','relation':'coupled state','task':'derive implication after learning','mode':'join'}
     path=run/'stages'/sid/'workspace/result.json';write(path,r);return path,r
    definitions=SimpleNamespace(request=lambda q:{'question':q,'status':'unknown','facts':[]})
    args=SimpleNamespace(model='fake',effort='low',timeout=2,check_timeout=2,executor='api',development_periods=0,hypothesis_rounds=4,max_researchers=6,definition_service=definitions)
    memory=runner.Memory(root/'memory');domains=[(f'r{i}','same field') for i in range(count)]
    with patch.object(runner.lab,'LAB',labdir),patch.object(runner.lab,'inside',side_effect=lambda p:Path(p).resolve()),patch('learning_support.inside',side_effect=lambda p:Path(p).resolve()),patch.object(runner.lab,'stage_run',side_effect=stage),patch.dict(runner.lab.CASES,{'synthetic':domains}):
     with self.assertRaises(InterruptedError):runner.lab.run_case('synthetic',root/'run',args,memory)
     with self.assertRaises(runner.GenerationFrozen):runner.lab.run_case('synthetic',root/'run',args,memory)
     self.assertTrue(json.loads((root/'run/ideas.json').read_text())['ideas'])
     self.assertTrue(json.loads((root/'run/candidate_history.json').read_text())['current_hypotheses'])
     self.assertNotIn('08_fresh_continuation',calls)
     self.assertEqual(len([s for s in calls if s.startswith('09_develop_') and '_learn_' not in s]),4)
     self.assertEqual(len([s for s in calls if s.startswith('09_develop_') and '_learn_' in s]),1)
     events=json.loads((root/'run/research_rounds/events.json').read_text())
     self.assertIn('09_develop_000_learn_0',events[0]['decision_source'])
     self.assertEqual(events[0]['next_move']['focus'],'Post-learning relation')
     self.assertEqual(len([s for s in calls if s.startswith('09_onboard_')]),1)
     before=list(calls)
     runner.lab.run_case('synthetic',root/'run',args,memory)
     self.assertEqual(before,calls)
     freeze=json.loads((root/'run/GENERATION_FREEZE.json').read_text())
     for p,sha in freeze['files'].items():self.assertEqual(hashlib.sha256(Path(p).read_bytes()).hexdigest(),sha)


class PrivateTransportTests(unittest.TestCase):
 def test_hidden_original_requires_private_capability_and_logs_stay_private(self):
  import importlib.util
  spec=importlib.util.spec_from_file_location('private_gateway',Path(__file__).with_name('model_gateway.py'))
  g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);(root/'controller_only').mkdir();(root/'controller_only/gateway.capability').write_text('test-capability')
   payload={'messages':[{'role':'user','content':'10.1038/s41586-026-10891-z'}],'max_tokens':400}
   cfg={'model':'fake','api_style':'chat','budgets':{'generation':{'calls':3,'input_tokens':10000,'output_tokens':2000}}}
   fake=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kw:SimpleNamespace(model_dump=lambda:{'choices':[{'message':{'content':'{}'}}],'usage':{'prompt_tokens':20,'completion_tokens':4}}))))
   with patch.object(g,'ROOT',root),patch.object(g,'CFG',cfg),patch.object(g,'client',return_value=fake) as model:
    with self.assertRaises(ValueError):g.invoke('optical/ours/generation',payload)
    with self.assertRaisesRegex(ValueError,'private controller capability'):g.invoke('optical/definition_service/generation',payload)
    g.invoke('optical/definition_service/generation',payload,controller_token='test-capability')
    self.assertEqual(model.call_count,1)
    self.assertFalse((root/'runs').exists())
    logs=list((root/'controller_only/model_calls').rglob('*.json'))
    self.assertTrue(logs)
    self.assertTrue(all('test-capability' not in p.read_text() for p in logs))



class AdapterDisclosureTests(unittest.TestCase):
 def test_real_tool_loop_keeps_originals_out_of_researcher_messages(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);(root/'cases/optical').mkdir(parents=True)
   shutil.copy2(runner.ROOT/'cases/optical/measurements.csv',root/'cases/optical/measurements.csv')
   private=root/'controller_only/optical';private.mkdir(parents=True)
   original=private/'source.txt';original.write_text('The scale is 0–1. Hidden target: 10.1038/s41586-026-10891-z')
   write(private/'registered_sources.json',{'documents':[{'id':'O1','path':str(original),'sha256':hashlib.sha256(original.read_bytes()).hexdigest()}]})
   seen=[]
   def create(**kwargs):
    messages=kwargs['messages'];system=messages[0]['content'];seen.append(system)
    if 'isolated material reader' in system:
     result={'status':'released','facts':[{'statement':'The scale is 0–1.','source_id':'O1','quote':'The scale is 0–1.'}]}
     name='submit_service_result';arguments={'result':result}
    elif 'Independently check this proposed disclosure' in system:
     name='submit_service_result';arguments={'result':{'question_is_neutral':True,'answer_is_neutral':True,'supported':True}}
    else:
     self.assertNotIn('10.1038/s41586-026-10891-z',json.dumps(messages))
     if len(messages)==2:name='request_case_definition';arguments={'question':'What is the scale?'}
     else:
      self.assertIn('0–1',messages[-1]['content'])
      name='submit_result';arguments={'result':{'summary':'The registered scale is 0–1.',**{k:[] for k in ['artifacts','evidence','claims','limitations','next_actions']}}}
    message={'role':'assistant','tool_calls':[{'id':'call'+str(len(seen)),'type':'function','function':{'name':name,'arguments':json.dumps(arguments)}}]}
    return SimpleNamespace(choices=[SimpleNamespace(finish_reason='tool_calls',message=SimpleNamespace(model_dump=lambda **kw:message))])
   api=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
   source=root/'brief.json';write(source,{'task':'Fixture case'})
   with patch.object(runner,'PROJECT',root/'project'):
    adapter=runner.StageAdapter(root,'optical','generation',{'model':'fake'},'closed',api=api)
    path,result=adapter(adapter.run,'probe','auditor','Read the scale definition.',[source],'fake','low',2)
   self.assertEqual(len(seen),4)
   for p in (adapter.run/'stages/probe').rglob('*.json'):
    self.assertNotIn('10.1038/s41586-026-10891-z',p.read_text())
   self.assertTrue(list((private/'service_calls').rglob('*.json')))

if __name__=='__main__':unittest.main()
