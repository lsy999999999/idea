import unittest,tempfile
from pathlib import Path
import run_ours as r
class ReferenceHandoffs(unittest.TestCase):
 def test_paraphrases_and_document_references_do_not_need_duplicate_quotes(self):
  packet={'version':'hypothesis-cycle-v1','sources':{'doc':'Actual source'},'required_service_uptake':[],'peer_sources':[]}
  result={'development_step':{'focus':{'source':'doc'},'gap':'conceptual gap','reason':'why now','action':'derive','expected_change':'a conditional relation','uptake':[{'source':'doc','effect':'unchanged','quote':None,'reason':'Read source; no change yet','consequence':None}],'outcome':{'kind':'relation','statement':'Conditional authored relation retained in this result.','remaining_gap':'scope unresolved'}},'learning_request':{'needed':True,'gap':'compressed gap','why_now':'paraphrased reason'}}
  r.validate_step(result,packet)
  result['development_step']['focus']['source']='invented'
  with self.assertRaises(ValueError):r.validate_step(result,packet)
 def test_omitted_state_edits_keep_existing_content_and_versions_are_controller_bound(self):
  with tempfile.TemporaryDirectory() as td:
   store=r.ContextStore(Path(td));store.add('/supplied','Actual source')
   a=object.__new__(r.StageAdapter)
   context={'question_state':{'self':{'ref':{'id':'personal:a','owner':'a','version':2},'question':'Original question'}},'hypothesis_state':{'self':[{'ref':{'key':'h','version':3}}]}}
   original={'summary':'Authored summary','artifacts':[],'hypothesis_updates':[{'key':'h','base_version':0,'assumption':'Authored conditional assumption'}]}
   out=a.normalize(original,{},store,context)
   self.assertEqual(out['personal_question_update']['question'],'Original question')
   self.assertTrue(out['personal_question_update']['controller_default'])
   self.assertEqual(out['hypothesis_updates'][0]['base_version'],3)
   self.assertEqual(out['hypothesis_updates'][0]['assumption'],original['hypothesis_updates'][0]['assumption'])
   self.assertNotIn('personal_question_update',original)
 def test_source_use_object_keeps_original_and_does_not_invent_reading(self):
  with tempfile.TemporaryDirectory() as td:
   store=r.ContextStore(Path(td));a=object.__new__(r.StageAdapter)
   raw={'broker_reply_source_ids':['K1'],'uses':[{'source':'other','use':'Authored note'}]}
   out=a.normalize({'summary':'s','source_use':raw},{},store,{'development_cycle':{'sources':{}},'broker_reply_source_ids':['K1']})
   self.assertEqual(out['source_use_author_submission'],raw)
   self.assertEqual(out['source_use'][0]['source_id'],'K1')
   self.assertTrue(out['source_use'][0]['controller_default'])
   self.assertIn('unconfirmed',out['source_use'][0]['reason'])
if __name__=='__main__':unittest.main()
