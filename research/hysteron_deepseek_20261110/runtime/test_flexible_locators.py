import unittest,tempfile
from pathlib import Path
from flexible_locator import select
from research_context import ContextStore
class Locators(unittest.TestCase):
 def test_slash_field_paths_and_unique_names(self):
  value={'data_dictionary':{'S1/S2/S3':'direction'}}
  for ref in ['/data_dictionary/S1/S2/S3','/data_dictionary/S1~1S2~1S3','S1/S2/S3']:
   self.assertEqual(select(value,ref),('direction','/data_dictionary/S1~1S2~1S3'))
  self.assertEqual(select({'a':{'b':'x'}},'a.b'),('x','/a/b'))
 def test_ambiguous_and_missing_stay_unresolved(self):
  for value,ref in [({'a':{'x':1},'b':{'x':2}},'x'),({'a/b':'x','a':{'b':'y'}},'/a/b'),({'x':1},'absent')]:
   with self.assertRaises(ValueError):select(value,ref)
 def test_filename_alias_is_scoped_and_unique(self):
  with tempfile.TemporaryDirectory() as td:
   s=ContextStore(Path(td));s.add('/registered/first.json','{"foo":"bar"}')
   self.assertEqual(s.read('first.json',pointer='foo')['text'],'"bar"')
   s.add('/other/first.json','{"foo":"baz"}')
   with self.assertRaises(ValueError):s.read('first.json')
if __name__=='__main__':unittest.main()
