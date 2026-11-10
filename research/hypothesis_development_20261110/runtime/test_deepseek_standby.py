import unittest,json,tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import test_transport
m=test_transport.g
class DeepSeekStandby(unittest.TestCase):
 def test_thinking_effort_and_tool_reasoning_are_preserved(self):
  seen=[]
  def create(**kw):
   seen.append(kw)
   raw={'choices':[{'message':{'role':'assistant','content':None,'reasoning_content':'opaque provider field','tool_calls':[{'id':'c1','type':'function','function':{'name':'read','arguments':'{}'}}]}}],'usage':{'prompt_tokens':10,'completion_tokens':5}}
   return SimpleNamespace(model_dump=lambda:raw)
  cfg={'model':'deepseek-flash','api_style':'chat','base_url':'https://api.deepseek.com','reasoning_effort':'low','chat_reasoning_parameter':'reasoning_effort','thinking_enabled':True,'budgets':{'probe':{'calls':3,'input_tokens':10000,'output_tokens':2000}}}
  api=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
  with tempfile.TemporaryDirectory() as td,patch.object(m,'ROOT',Path(td)),patch.object(m,'CFG',cfg),patch.object(m,'client',return_value=api):
   r=m.invoke('test/deepseek/probe',{'messages':[{'role':'user','content':'fixture'}],'max_tokens':400})
   message=r['choices'][0]['message']
   m.invoke('test/deepseek/probe',{'messages':[{'role':'user','content':'fixture'},message,{'role':'tool','tool_call_id':'c1','content':'fixture result'}],'max_tokens':400})
   self.assertEqual(seen[0]['reasoning_effort'],'low')
   self.assertEqual(seen[0]['extra_body'],{'thinking':{'type':'enabled'}})
   self.assertEqual(seen[1]['messages'][1]['reasoning_content'],message['reasoning_content'])
if __name__=='__main__':unittest.main()
