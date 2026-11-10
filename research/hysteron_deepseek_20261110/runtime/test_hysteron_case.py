import unittest,json,csv,hashlib
from pathlib import Path
from run_ours import ROOT
from case_access import actor_brief,assert_measurements,locked_policy
from knowledge_broker import SourcePolicy
class HysteronCaseTests(unittest.TestCase):
 def test_empirical_extraction_and_boundary(self):
  rows=list(csv.DictReader((ROOT/'cases/hysteron/measurements.csv').open()))
  self.assertEqual(len(rows),123)
  self.assertEqual(sum(r['record_type']=='threshold' for r in rows),40)
  self.assertEqual([float(r['drive_gamma_cm']) for r in rows if r['configuration_id']=='pair_A' and r['rotor_i']=='1' and r['direction']=='up' and r['other_state']=='-1'],[7.3,7.1,6.5,5.5])
  self.assertEqual([int(r['event_index']) for r in rows if r['record_type']=='state_event'],list(range(1,17)))
  assert_measurements('hysteron',ROOT/'cases/hysteron/measurements.csv')
  policy=SourcePolicy(locked_policy('hysteron'))
  self.assertTrue(policy.forbidden('arxiv 2409.07726'))
  self.assertTrue(policy.forbidden('10.1038/s41467-026-70913-2'))
 def test_neutral_apparatus_reaches_researchers(self):
  d=json.loads((ROOT/'cases/hysteron/dossier.json').read_text())
  b=actor_brief('hysteron',d)
  self.assertIn('protocol',b);self.assertIn('apparatus',b)
  self.assertEqual(b['knowledge_before_exclusive'],'2024-09-12')
  self.assertNotIn('controller_only',json.dumps(b))
 def test_no_model_cells(self):
  p=json.loads((ROOT/'controller_only/hysteron/CELL_PROVENANCE.json').read_text())
  for r in p['records']:
   if r['sheet']=='Fig.2A':
    self.assertTrue(all(x[0] in 'ABCDEFGHIJKLMNOP' and not x[1].isalpha() for x in r['cells']))
   if r['sheet']=='Fig.3B':self.assertTrue(all(x[0] in 'AB' for x in r['cells']))
if __name__=='__main__':unittest.main()
