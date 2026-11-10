import unittest,tempfile,json,threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from openai.types.chat import ChatCompletion
import common

def reply(finish='stop',content='Complete substantive hypothesis'):
 return ChatCompletion.model_validate({'id':'mock','object':'chat.completion','created':0,'model':'deepseek-flash','choices':[{'index':0,'finish_reason':finish,'message':{'role':'assistant','content':content}}],'usage':{'prompt_tokens':10,'completion_tokens':20,'total_tokens':30}})

class TransportTests(unittest.TestCase):
 def engine(self,path,responses):
  e=common.Engine.__new__(common.Engine);e.system='offline';e.out=path;e.lock=threading.RLock();e.reasons={};e.sent=[]
  def create(**kw):e.sent.append(kw);return responses.pop(0)
  e.api=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
  return e
 def test_thinking_uses_auto_tools(self):
  with tempfile.TemporaryDirectory() as d,patch.object(common,'ROOT',Path(d)):
   e=self.engine(Path(d),[reply()]);e.raw([{'role':'user','content':'x'}],tools=[{'type':'function','function':{'name':'x'}}],tool_choice={'type':'function','function':{'name':'x'}},private=True)
   self.assertNotIn('tool_choice',e.sent[0]);self.assertEqual(e.sent[0]['reasoning_effort'],'high')
 def test_truncation_expands_and_resume_reuses(self):
  with tempfile.TemporaryDirectory() as d,patch.object(common,'ROOT',Path(d)):
   e=self.engine(Path(d),[reply('length'),reply()]);messages=[{'role':'user','content':'x'}]
   e.raw(messages,private=True)
   self.assertGreater(e.sent[1]['max_tokens'],e.sent[0]['max_tokens'])
   self.assertGreaterEqual(e.sent[1]['max_tokens'],65536)
   e.raw(messages,private=True);self.assertEqual(len(e.sent),2)
   self.assertEqual(len((Path(d)/'usage.jsonl').read_text().splitlines()),2)
 def test_upstream_heading_adaptation(self):
  with tempfile.TemporaryDirectory() as d:
   raw='**Problem:** actual problem\n\n**Rationale (measured relations).** actual rationale'
   e=SimpleNamespace(out=Path(d),run=lambda m:SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=raw))]))
   result=common.Proxy(e).call([])
   self.assertIn('Problem: actual problem',result);self.assertIn('Rationale: actual rationale',result)
   record=json.loads(next((Path(d)/'format_adaptations').glob('*.json')).read_text());self.assertEqual(record['raw'],raw)

if __name__=='__main__':unittest.main()
