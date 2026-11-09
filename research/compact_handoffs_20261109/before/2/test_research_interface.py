"""Offline regressions for real failures in the v1 inquiry interface."""
import hashlib, importlib.util, json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from research_context import ContextStore, dumps
from research_tools import ResearchTools
import run_ours as runner
from run_ours import StageAdapter
ROOT=Path(__file__).resolve().parents[1]

class ContextTests(unittest.TestCase):
 def test_nested_review_is_lossless_and_deduplicated(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);source=root/'material.json';text=json.dumps({'finding':'exact scientific statement '*2000});source.write_text(text)
   context=root/'context.json';context.write_text(json.dumps({'development_cycle':{'version':'hypothesis-cycle-v1','sources':{str(source):text}}}))
   review=root/'review.json';review.write_text(json.dumps({'sources':{'s'+str(i):{'before_inputs':[{'path':str(source),'text':text,'sha256':hashlib.sha256(text.encode()).hexdigest()},{'path':str(context),'text':context.read_text()}]} for i in range(8)}}))
   store=ContextStore(root/'store');top=store.prepare([review]);packet=store.packet(top)
   self.assertLess(len(dumps(packet)),len(review.read_text())//10)
   ref=store.paths[str(source)];parts=[];offset=0
   while True:
    row=store.read(ref,offset=offset,limit=12000,raw=True);parts.append(row['text']);offset=row['next_offset']
    if offset is None:break
   self.assertEqual(''.join(parts),text)
   restored=ContextStore(root/'store');self.assertEqual(restored.documents[ref]['text'],text)
   with self.assertRaises(ValueError):store.read('/Users/LSY/.codex/auth.json')
 def test_corrupted_snapshot_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'x.json';p.write_text(json.dumps({'path':'/not/read','text':'data','sha256':'wrong'}))
   with self.assertRaisesRegex(ValueError,'hash mismatch'):ContextStore(Path(td)/'store').prepare([p])
 def test_quotes_are_not_summarized(self):
  with tempfile.TemporaryDirectory() as td:
   store=ContextStore(td);ref=store.add('/source','A specific exception contradicts the hypothesis.');store.prepare([])
   self.assertEqual(store.read(ref,raw=True)['text'],'A specific exception contradicts the hypothesis.')

class ToolTests(unittest.TestCase):
 def make(self,td,broker=None):
  return ResearchTools(ContextStore(Path(td)/'documents'),Path(td),{'measurements':ROOT/'cases/optical/measurements.csv'},broker,runner.expression)
 def test_full_csv_and_units(self):
  with tempfile.TemporaryDirectory() as td:
   t=self.make(td)
   def mean(group):return t.analyze('measurements','scan',group,[],[{'name':'m','expression':'mean(DOP)'}])
   a,b=mean('spread'),mean('mean_phase');self.assertEqual(a['selected_rows'],102);self.assertEqual(b['selected_rows'],200)
   self.assertAlmostEqual(a['outputs']['m']['value']/100/b['outputs']['m']['value'],0.7190206332982817,places=12)
   norm=t.analyze('measurements','scan','mean_phase',[],[{'name':'n','expression':'mean(S1**2+S2**2+S3**2)'}])
   self.assertAlmostEqual(norm['outputs']['n']['value'],0.9999956376501004,places=12)
 def test_tool_errors_do_not_become_scientific_results(self):
  with tempfile.TemporaryDirectory() as td:
   t=self.make(td);r=t.call('analyze_csv',{'dataset':'missing','outputs':[{'name':'x','expression':'mean(DOP)'}]},'a')
   self.assertEqual(r['status'],'error')
   for expr in ['__import__("os").system("whoami")','[1]*100000000','diff(DOP,n=100000000)','(10**12)**12']:
    with self.assertRaises((ValueError,TypeError)):t.analyze('measurements',None,None,[],[{'name':'x','expression':expr}])
 def test_arrays_explicitly_paged_and_cached(self):
  with tempfile.TemporaryDirectory() as td:
   t=self.make(td);args={'dataset':'measurements','group_column':'scan','group_value':'spread','variables':[],'outputs':[{'name':'all','expression':'DOP/100'}]}
   a=t.call('analyze_csv',args,'a');b=t.call('analyze_csv',args,'b');self.assertEqual(a,b)
   self.assertTrue(a['outputs']['all']['truncated'])
   ref=a['outputs']['all']['full_value_ref'];self.assertEqual(len(json.loads(t.store.read(ref,raw=True)['text'])['value']),102)
   restored=self.make(td);self.assertEqual(a,restored.call('analyze_csv',args,'c'));self.assertTrue(restored.store.read(ref,raw=True))
 def test_batch_documents_preserves_exact_pages(self):
  with tempfile.TemporaryDirectory() as td:
   t=self.make(td);a=t.store.add('/a','first exact page');b=t.store.add('/b','second exact page')
   requests=[{'ref':r,'pointer':'','offset':0,'limit':100,'raw':True} for r in [a,b]]
   result=t.call('read_documents',{'requests':requests},'batch')
   self.assertEqual([x['text'] for x in result['documents']],['first exact page','second exact page'])
   for x in requests:x['limit']=12001
   self.assertEqual(t.call('read_documents',{'requests':requests},'over')['status'],'error')
 def test_dataset_mutation_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   path=Path(td)/'x.csv';path.write_text('x\n1\n2\n');store=ContextStore(Path(td)/'docs');t=ResearchTools(store,Path(td),{'x':path},expression=runner.expression);path.write_text('x\n9\n')
   with self.assertRaisesRegex(ValueError,'changed'):t.analyze('x',outputs=[{'name':'m','expression':'mean(x)'}])
 def test_actual_broker_reply_is_readable_and_reused(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);broker=runner.KnowledgeBroker(root/'knowledge',runner.SourcePolicy({'knowledge_before_exclusive':'2026-11-10','excluded_dois':[],'excluded_titles':[],'retrieval_results_per_query':1,'read_full_text':False}),
     lambda url:json.dumps({'resultList':{'result':[{'firstPublicationDate':'2020-01-01','doi':'10.1/test','title':'Fixture foundation','abstractText':'A concrete readable relation.'}]} }) if 'europepmc' in url else json.dumps({}))
   t=self.make(td,broker);a=t.call('search_sources',{'queries':['fixture relation']},'a');self.assertEqual(a['status'],'read_content_returned')
   s=a['sources'][0];self.assertTrue(Path(s['local_path']).exists());self.assertIn('concrete readable',t.store.read(s['ref'],raw=True)['text'])
   with patch.object(broker,'search',side_effect=AssertionError('must reuse')):self.assertEqual(a,t.call('search_sources',{'queries':['fixture relation']},'b'))

class ContractTests(unittest.TestCase):
 def test_json_quote_selector_preserves_value_and_rejects_conflicting_prose(self):
  with tempfile.TemporaryDirectory() as td:
   store=ContextStore(td);text='Exported normalized polarization-direction components.'
   store.add('/source',json.dumps({'data_dictionary':{'S1/S2/S3':text}}))
   a=object.__new__(StageAdapter)
   value={'development_step':{'focus':{'source':'S1','quote':'S1/S2/S3: '+text},'uptake':[]}}
   with self.assertRaisesRegex(ValueError,'exact source string value.*Exported normalized'):
    a.normalize(value,{'S1':'/source'},store)
   value['development_step']['focus']={'source':'S1','quote_pointer':'/data_dictionary/S1~1S2~1S3'}
   result=a.normalize(value,{'S1':'/source'},store)
   self.assertEqual(result['development_step']['focus']['quote'],text)
   self.assertNotIn('quote',value['development_step']['focus'])
   value['development_step']['focus']['quote']='a different scientific claim'
   with self.assertRaisesRegex(ValueError,'conflicts'):a.normalize(value,{'S1':'/source'},store)
 def test_reference_binding_no_silent_semantic_repair(self):
  with tempfile.TemporaryDirectory() as td:
   store=ContextStore(td);store.add('/source','actual quote')
   a=object.__new__(StageAdapter)
   result={'development_step':{'focus':{'source':'S1','quote':'actual quote'},'gap':'gap','reason':'reason','uptake':[]},'learning_request':{'needed':True,'context_ref':'development_step'}}
   out=a.normalize(result,{'S1':'/source'},store)
   self.assertEqual(out['learning_request']['gap'],'gap');self.assertEqual(out['development_step']['focus']['source'],'/source');self.assertNotIn('gap',result['learning_request'])
   result['learning_request']['gap']='different claim'
   with self.assertRaisesRegex(ValueError,'conflicts'):a.normalize(result,{'S1':'/source'},store)
 def test_no_invalid_json_salvage(self):
  with self.assertRaises(json.JSONDecodeError):StageAdapter.parse('{"summary":"x"}}')
 def test_closed_mode_is_explicit_and_online_is_default(self):
  self.assertIn("default=cfg.get('knowledge','online')",Path(runner.__file__).read_text())
 def test_public_fetch_does_not_read_private_targets(self):
  with tempfile.TemporaryDirectory() as td:
   fetch=runner.PublicFetcher(Path(td)/'calls.json')
   for url in ['http://127.0.0.1/','https://localhost/','https://u:p@api.crossref.org/','file:///etc/passwd']:
    with self.assertRaises(ValueError):fetch(url)


class AdapterLoopTests(unittest.TestCase):
 def test_data_call_invalid_submission_repair_and_resume(self):
  import shutil
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);case=root/'cases/optical';case.mkdir(parents=True);shutil.copy2(ROOT/'cases/optical/measurements.csv',case/'measurements.csv')
   source=root/'input.json';source.write_text('{"task":"Compute actual CSV means and save a result"}')
   turns=[]
   result={'summary':'Read all 302 rows.','artifacts':[],'evidence':[],'claims':[],'limitations':[],'next_actions':[]}
   replies=[('analyze_csv',{'dataset':'measurements','group_column':None,'group_value':None,'variables':[],'outputs':[{'name':'count','expression':'sum(isfinite(DOP))'}]}),('submit_result',{'result':{**result,'summary':[]}}),('submit_result',{'result':result})]
   def create(**kw):
    turns.append(kw)
    if len(turns)==3:
     self.assertIn('summary must be',kw['messages'][-1]['content'])
     self.assertFalse((root/'project/runs/api_v2_optical_generation/stages/test/api_v2/workspace/result.json').exists())
    name,args=replies[len(turns)-1];message={'role':'assistant','tool_calls':[{'id':'call'+str(len(turns)),'type':'function','function':{'name':name,'arguments':json.dumps(args)}}]}
    return SimpleNamespace(choices=[SimpleNamespace(finish_reason='tool_calls',message=SimpleNamespace(model_dump=lambda **kw:message))])
   api=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
   with patch.object(runner,'PROJECT',root/'project'):
    adapter=StageAdapter(root,'optical','generation',{'model':'fake'},'closed',api)
    self.assertFalse(adapter.run.exists(), 'Memory initialization must not pre-create native run')
    path,value=adapter(adapter.run,'test','auditor','Inspect data',[source],'fake','low',20)
    self.assertEqual(value['summary'],result['summary']);self.assertEqual(len(turns),3)
    self.assertEqual(adapter(adapter.run,'test','auditor','Inspect data',[source],'fake','low',20),(path,value));self.assertEqual(len(turns),3)
    with self.assertRaisesRegex(ValueError,'inputs changed'):adapter(adapter.run,'test','auditor','Different prompt',[source],'fake','low',20)

class StartupTests(unittest.TestCase):
 def test_native_material_recovery_keeps_previously_read_body_in_initial_inputs(self):
  import shutil
  class ReachedInitial(BaseException):pass
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);labdir=root/'learning_lab';(labdir/'scenarios').mkdir(parents=True)
   shutil.copy2(runner.lab.LAB/'scenarios/optical.md',labdir/'scenarios/optical.md')
   shutil.copy2(runner.lab.LAB/'PLAN_SOURCE.md',labdir/'PLAN_SOURCE.md')
   body='A previously read concrete full-body relation.';abstract='A later weaker abstract.'
   docs=[]
   for i,text in enumerate([body,abstract]):
    path=root/f'source_{i}.txt';path.write_text(text);docs.append(path)
   def fake_stage(run,sid,role,prompt,inputs,*args):
    if sid.startswith('02_initial'):
     archived=[p.read_text() for p in inputs if p.parent==labdir/'library']
     self.assertIn(body,archived);self.assertIn(abstract,archived)
     catalog=json.loads((run/'source_catalog.json').read_text())
     self.assertEqual(len(catalog['materials_history']),2)
     self.assertEqual(len(catalog['sources']),3)
     self.assertIn('review',[x['source_kind'] for x in catalog['sources']])
     raise ReachedInitial()
    self.assertIn(sid,['01_materials','01_materials_recovery'])
    index=int(sid.endswith('_recovery'));path=run/'stages'/sid/'result.json';path.parent.mkdir(parents=True)
    result={'summary':'material record','materials':[{'id':'m'}],'sources':[{
     'id':'same-source-id','local_path':str(docs[index]),'url':'https://example.org/paper','title':'Original study',
     'content_access':'excerpt','domain_relation':'direct','relevance_reason':'Relevant relation',
     'source_kind':'original_study','supporting_quote':docs[index].read_text()}]}
    if index:
     result['sources'].append({**result['sources'][0],'local_path':str(docs[0]),
                              'source_kind':'review','supporting_quote':body})
    path.write_text(json.dumps(result));return path,result
   args=SimpleNamespace(model='fake',effort='low',timeout=2,check_timeout=2,executor='api',development_periods=0)
   memory=runner.Memory(root/'memory')
   with patch.object(runner.lab,'LAB',labdir),patch.object(runner.lab,'inside',side_effect=lambda p:Path(p).resolve()),patch('learning_support.inside',side_effect=lambda p:Path(p).resolve()),patch.object(runner.lab,'stage_run',side_effect=fake_stage),patch.dict(runner.lab.CASES,{'optical':[('scientist','optics')]}):
    with self.assertRaises(ReachedInitial):runner.lab.run_case('optical',root/'run',args,memory)
 def test_native_controller_reaches_first_stage(self):
  import shutil
  class ReachedStage(BaseException):pass
  with tempfile.TemporaryDirectory() as td:
   root=Path(td)
   (root/'cases/optical').mkdir(parents=True)
   shutil.copy2(ROOT/'cases/optical/measurements.csv',root/'cases/optical/measurements.csv')
   with patch.object(runner,'PROJECT',root/'project'), patch.object(runner.lab,'stage_run'), patch.dict(runner.lab.CASES,{}):
    adapter=StageAdapter(root,'optical','generation',{'model':'fake'},'closed',api=object())
    self.assertFalse(adapter.run.exists())
    with patch.object(StageAdapter,'__call__',side_effect=ReachedStage):
     with self.assertRaises(ReachedStage):adapter.generation()
    self.assertTrue((adapter.run/'learning_state.json').exists())
 def test_reports_all_common_field_errors_together(self):
  adapter=object.__new__(StageAdapter)
  with self.assertRaisesRegex(ValueError,'artifacts must be an array; evidence must be an array; claims must be an array'):
   adapter.validate({'summary':'x'},'test','auditor',{},[])
 def test_material_document_id_resolves_exact_file(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);p=root/'source.json';p.write_text('{"title":"real source"}')
   store=ContextStore(root/'store');ref=store.add_file(p)
   adapter=object.__new__(StageAdapter)
   result=adapter.normalize({'sources':[{'local_path':ref}]},{},store)
   self.assertEqual(result['sources'][0]['local_path'],str(p.resolve()))

class FinalContractTests(unittest.TestCase):
 def test_missing_declared_artifact_rejected_and_summary_materialized(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);adapter=object.__new__(StageAdapter);store=ContextStore(root/'docs')
   with self.assertRaisesRegex(ValueError,'does not exist'):
    adapter.validate_artifacts({'artifacts':['imaginary.md']},root)
   result=adapter.normalize({'summary':'An exact conditional hypothesis.','artifacts':[]},{},store)
   adapter.validate_artifacts(result,root)
   self.assertEqual(next(iter(result['files'].values())),'An exact conditional hypothesis.\n')
 def test_review_feedback_names_actual_quote_stage_and_note_keys(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);(root/'internal_review').mkdir();(root/'internal_review/inputs.json').write_text(json.dumps({'sources':{'stage_a':{'files':[{'text':'a quote'}],'result':{'memory_notes':[]}},'stage_b':{'files':[{'text':'actual exact quote'}],'result':{'memory_notes':[]}}}}))
   adapter=object.__new__(StageAdapter);adapter.run=root;adapter.owners=[]
   result={'summary':'x',**{k:[] for k in ['artifacts','evidence','claims','limitations','next_actions']},'findings':[{'id':'f','source_stage':'stage_a','quote':'actual exact quote','note_keys':['summary']}]}
   with self.assertRaisesRegex(ValueError,'stage_b.*note_keys refers to actual memory notes'):
    adapter.validate(result,'04_internal_review','reviewer',{},[])

class ContinuationIsolationTests(unittest.TestCase):
 def test_memory_probe_does_not_receive_data_or_search_tools_or_require_live_state(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);source=root/'fresh_continuation.json';source.write_text('{"retrieved":[]}');seen=[]
   def create(**kw):
    seen.append(kw)
    self.assertEqual({t['function']['name'] for t in kw['tools']},{'read_document','read_documents','submit_result'})
    self.assertEqual(json.loads(kw['messages'][1]['content'])['datasets'],[])
    value={'summary':'Only saved memory was supplied.',**{k:[] for k in ['artifacts','evidence','claims','limitations','next_actions']}}
    message={'role':'assistant','tool_calls':[{'id':'submit','type':'function','function':{'name':'submit_result','arguments':json.dumps({'result':value})}}]}
    return SimpleNamespace(choices=[SimpleNamespace(finish_reason='tool_calls',message=SimpleNamespace(model_dump=lambda **kw:message))])
   api=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
   with patch.object(runner,'PROJECT',root/'project'):
    adapter=StageAdapter(root,'optical','generation',{'model':'fake','continuation_mode':'memory_only_probe'},api=api)
    _,value=adapter(adapter.run,'08_fresh_continuation','theory_scientist','Continue from memory',[source],'fake','low',20)
    self.assertEqual(len(seen),1)

if __name__=='__main__':unittest.main()
