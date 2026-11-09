"""Adversarial workflow regressions, not scientific performance measurements."""
import copy,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from learning_support import audit_review,review_packet,validate_uptake,validate_memory_use,HypothesisState
from learning_memory import digest
from discover import write

class ReviewIntegrityTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
 def packet(self):
  self.note={'key':'relation','understanding':'If A holds, B may occur.','conditions':'Only under A','example':'Illustrative','open_questions':'Does A hold?','kind':'hypothesis'}
  p=self.root/'result.json';write(p,{'memory_notes':[self.note]})
  return review_packet({'original':('A',p)})
 def finding(self):
  return {'id':'f','source_stage':'original','quote':'If A holds, B may occur.','kind':'logic','status':'needs_correction','reason':'B is absent in an unrelated sample','note_keys':['relation']}
 def test_conditional_claim_is_not_refuted_by_a_reviewer_label(self):
  report=audit_review({'findings':[self.finding()]},self.packet())
  f=report['findings'][0];self.assertEqual(f['status'],'undetermined');self.assertEqual(f['reviewer_status'],'needs_correction');self.assertEqual(f['verification_level'],'quote_provenance_only')
 def test_arbitrary_arithmetic_mismatch_is_not_a_verified_textual_error(self):
  f={**self.finding(),'kind':'arithmetic','calculation':{'bindings':{'x':2},'expression':'x+1','expected':9}}
  row=audit_review({'findings':[f]},self.packet())['findings'][0]
  self.assertFalse(row['recomputation']['matches_expected']);self.assertEqual(row['status'],'undetermined');self.assertEqual(row['verification_level'],'recomputed_expression_only')
 def test_accepted_correction_cannot_only_change_the_label_but_rebuttal_can_retain_content(self):
  report=audit_review({'findings':[self.finding()]},self.packet())
  result={'verification_responses':[{'finding_id':'f','stance':'accept','reason':'Accept'}],'memory_notes':[{**self.note,'kind':'correction','revision_reason':'Updated label'}]}
  with self.assertRaisesRegex(ValueError,'affected content'):validate_uptake(result,report,'A')
  result['verification_responses'][0]['stance']='rebut';validate_uptake(result,report,'A')
  result['verification_responses'][0]['stance']='accept';result['memory_notes'][0]['conditions']='Requires A and a bounded domain';validate_uptake(result,report,'A')
 def test_fresh_memory_use_cannot_invent_note_version_or_origin(self):
  packet={'retrieved':[{'note':{'key':'k','version':2,'source_task':'old'}}]}
  use={'key':'k','version':2,'source_task':'old','used_for':'Conditional derivation','scope_check':'Only under A'}
  validate_memory_use({'memory_use':[use]},packet)
  for change in [{'key':'invented'},{'version':1},{'source_task':'other'}]:
   with self.assertRaises(ValueError):validate_memory_use({'memory_use':[{**use,**change}]},packet)
 def test_long_review_sources_are_not_truncated_while_claiming_full_hash(self):
  p=self.root/'result.json';write(p,{'summary':'x'*100001+'TAIL_MARKER'})
  row=review_packet({'long':('A',p)})['sources']['long']['files'][0]
  self.assertIn('TAIL_MARKER',row['text']);self.assertEqual(row['text'],p.read_text());self.assertEqual(row['sha256'],digest(p))

class DependencyIntegrityTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name);self.state=HypothesisState(self.root/'state',['A','B','C']);self.n=0
 def card(self,key,base=0,**kw):
  return {'key':key,'base_version':base,'assumption':'Conditional relation '+key,'motivation':'A gap','conceptual_move':None,'implications':[],'open_questions':[],'status':'developing','reason':'Develop','influenced_by':[],'depends_on':[],**kw}
 def save(self,owner,card,responses=None):
  self.n+=1;stage='s'+str(self.n);packet=self.state.packet(stage,owner);result={'hypothesis_updates':[card],'dependency_responses':responses or []};p=self.root/(stage+'.json');write(p,result);self.state.accept(stage,owner,result,p,packet)
  return next(c['ref'] for c in self.state.current() if c['ref']['owner']==owner and c['ref']['key']==card['key'])
 def test_changed_premise_flags_transitive_dependents_without_discarding_them(self):
  a1=self.save('A',self.card('a'));b1=self.save('B',self.card('b',depends_on=[a1]));c1=self.save('C',self.card('c',depends_on=[b1]));a2=self.save('A',self.card('a',1,assumption='Revised premise'))
  pb=self.state.packet('review_b','B');pc=self.state.packet('review_c','C');self.assertEqual(pb['revision_obligations'][0]['causes'][0]['latest_ref'],a2);self.assertEqual(pc['revision_obligations'][0]['causes'][0]['reason'],'dependency_awaiting_review');self.assertEqual(len(self.state.current()),3)
  with self.assertRaisesRegex(ValueError,'dependency obligation'):self.state.validate('review_b','B',{'hypothesis_updates':[]},pb)
  self.state.validate('review_b','B',{'hypothesis_updates':[],'dependency_responses':[{'ref':b1,'action':'unresolved','reason':'The alternative remains open'}]},pb)
  b2=self.save('B',self.card('b',1,depends_on=[a2]),[{'ref':b1,'action':'reaffirm','reason':'The same consequence still follows under the revised premise'}])
  self.assertFalse(self.state.packet('done_b','B')['revision_obligations']);self.assertEqual(self.state.packet('next_c','C')['revision_obligations'][0]['causes'][0]['latest_ref'],b2)
  b=next(x for x in self.state.current() if x['ref']==b2);self.assertFalse(b['conceptual_content_changed'])
 def test_influence_is_not_treated_as_logical_dependency(self):
  a=self.save('A',self.card('a'));self.save('B',self.card('b',influenced_by=[a]));self.save('A',self.card('a',1,assumption='New premise'));self.assertFalse(self.state.packet('read_b','B')['revision_obligations'])
 def test_unseen_and_self_dependencies_are_rejected(self):
  a=self.save('A',self.card('a'))
  with self.assertRaisesRegex(ValueError,'self dependency'):self.save('A',self.card('a',1,depends_on=[a]))
  with self.assertRaisesRegex(ValueError,'supplied refs'):self.save('B',self.card('b',depends_on=[{'owner':'Z','key':'absent','version':1}]))

if __name__=='__main__':unittest.main()
