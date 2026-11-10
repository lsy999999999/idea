import unittest,tempfile
from pathlib import Path
import run_ours as r
class Admission(unittest.TestCase):
 def test_exact_registered_measurement_and_literature_rules(self):
  with tempfile.TemporaryDirectory(dir=r.PROJECT) as td:
   a=object.__new__(r.StageAdapter);a.case='optical';a.root=r.ROOT;a.run=Path(td);a.owners=[]
   a.source_policy=r.SourcePolicy(r.locked_policy('optical'))
   brief=a.run/'allowed/measurements_brief.json';brief.parent.mkdir()
   expected=r.actor_brief('optical',r.read(r.lab.LAB/'scenarios/optical.md'));r.write(brief,expected)
   d={'summary':'Registered measurements','artifacts':[],'evidence':[],'claims':[],'limitations':[],'next_actions':[],
      'materials':[{'id':'m'}],'sources':[{'id':'B1','local_path':str(brief),'source_kind':'dataset',
       'content_access':'excerpt','domain_relation':'direct','relevance_reason':'Measurements',
       'supporting_quote':'DOP'}]}
   a.validate(d,'01_materials','curator',{},[])
   impostor=a.run/'unregistered.json';r.write(impostor,expected);d['sources'][0]['local_path']=str(impostor)
   with self.assertRaisesRegex(ValueError,'publication_date_unknown'):a.validate(d,'01_materials','curator',{},[])
   d['sources'][0]['local_path']=str(brief);r.write(brief,{**expected,'task':'altered'})
   with self.assertRaisesRegex(ValueError,'content changed'):a.validate(d,'01_materials','curator',{},[])
if __name__=='__main__':unittest.main()
