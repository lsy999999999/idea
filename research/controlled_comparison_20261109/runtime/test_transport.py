"""Offline transport tests: no model or network requests."""
import importlib.util,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('gateway',Path(__file__).with_name('model_gateway.py'));g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)

class Tests(unittest.TestCase):
 def test_tool_round_trip(self):
  data=g.responses_input([{'role':'assistant','content':None,'tool_calls':[{'id':'call1','function':{'name':'calculate','arguments':'{}'}}]},{'role':'tool','tool_call_id':'call1','content':'42'}])
  self.assertEqual(data[0]['call_id'],data[1]['call_id']);self.assertEqual(data[1]['output'],'42')
 def test_cache_and_budget_accounting(self):
  with tempfile.TemporaryDirectory() as tmp:
   cfg={'model':'fake','api_style':'chat','budgets':{'probe':{'calls':1,'input_tokens':2000,'output_tokens':600}}}
   fake=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kw:SimpleNamespace(model_dump=lambda:{'id':'test','model':'fake','choices':[{'message':{'content':'ok'}}],'usage':{'prompt_tokens':50,'completion_tokens':4}}))))
   payload={'model':'fake','messages':[{'role':'user','content':'hi'}],'max_tokens':400}
   with patch.object(g,'ROOT',Path(tmp)),patch.object(g,'CFG',cfg),patch.object(g,'client',return_value=fake) as call:
    first=g.invoke('test/system/probe',payload);self.assertEqual(first,g.invoke('test/system/probe',payload));self.assertEqual(call.call_count,1)
    ledger=json.loads((Path(tmp)/'runs/test/system/probe/usage.json').read_text());self.assertEqual(ledger['calls'],1);self.assertEqual(ledger['input_tokens'],50)
    with self.assertRaisesRegex(RuntimeError,'BUDGET_EXHAUSTED'):g.invoke('test/system/probe',{**payload,'messages':[{'role':'user','content':'different'}]})
    cfg['model']='other'
    with self.assertRaisesRegex(ValueError,'Model changed'):g.invoke('test/system/probe',payload)
 def test_estimator_is_not_byte_count(self):
  payload={'messages':[{'role':'user','content':'The sampling interval is 0.003333 seconds. '*500}]}
  self.assertLess(g.estimate_tokens(payload),len(json.dumps(payload).encode()))


class ResponseMappingTests(unittest.TestCase):
 def test_responses_format_strictness_and_reasoning_roundtrip(self):
  from types import SimpleNamespace
  with tempfile.TemporaryDirectory() as td:
   seen=[]
   raw={'id':'r1','model':'fake','status':'completed','output':[{'type':'reasoning','id':'reason1','summary':[],'encrypted_content':'opaque'},{'type':'function_call','call_id':'call1','name':'read','arguments':'{}'}],'usage':{'input_tokens':12,'output_tokens':5}}
   def create(**kw):
    seen.append(kw);return SimpleNamespace(id='r1',output=[SimpleNamespace(**o) for o in raw['output']],output_text='',model_dump=lambda **kw:raw)
   api=SimpleNamespace(responses=SimpleNamespace(create=create))
   cfg={'model':'fake','api_style':'responses','preserve_reasoning_items':True,'budgets':{'probe':{'calls':3,'input_tokens':10000,'output_tokens':2000}}}
   payload={'messages':[{'role':'user','content':'Return JSON'}],'max_tokens':400,'parallel_tool_calls':False,
    'response_format':{'type':'json_schema','json_schema':{'name':'x','schema':{'type':'object'},'strict':True}},
    'tools':[{'type':'function','function':{'name':'read','parameters':{'type':'object','properties':{},'additionalProperties':False},'strict':True}}]}
   with patch.object(g,'ROOT',Path(td)),patch.object(g,'CFG',cfg),patch.object(g,'client',return_value=api):
    result=g.invoke('test/response/probe',payload)
    self.assertTrue(seen[0]['tools'][0]['strict']);self.assertEqual(seen[0]['text']['format']['type'],'json_schema');self.assertFalse(seen[0]['parallel_tool_calls'])
    message=result['choices'][0]['message'];converted=g.responses_input([message,{'role':'tool','tool_call_id':'call1','content':'read result'}])
    self.assertEqual(converted[:2],raw['output']);self.assertEqual(converted[2]['call_id'],'call1')
    converted=g.responses_input([{'role':'assistant','provider_response_items':[{'type':'function_call','call_id':'c','async_':None,'caller':None}]}])
    self.assertNotIn('async_',converted[0]);self.assertNotIn('caller',converted[0])
    cfg['api_style']='chat'
    with self.assertRaisesRegex(ValueError,'transport settings changed'):g.invoke('test/response/probe',payload)
 def test_unknown_usage_is_not_zero_billed_usage(self):
  with tempfile.TemporaryDirectory() as td:
   cfg={'model':'fake','api_style':'chat','budgets':{'probe':{'calls':3,'input_tokens':10000,'output_tokens':1000}}}
   api=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kw:SimpleNamespace(model_dump=lambda:{'choices':[{'message':{'content':'x'}}],'usage':None}))))
   with patch.object(g,'ROOT',Path(td)),patch.object(g,'CFG',cfg),patch.object(g,'client',return_value=api):
    g.invoke('test/unknown/probe',{'messages':[{'role':'user','content':'x'}],'max_tokens':400})
    ledger=json.loads((Path(td)/'runs/test/unknown/probe/usage.json').read_text());self.assertEqual(ledger['usage_unknown_calls'],1);self.assertEqual(ledger['unknown_output_reserve'],400)
    (Path(td)/'runs/test/unknown/probe/FINAL_FREEZE.json').write_text('{}')
    with self.assertRaisesRegex(ValueError,'Frozen'):g.invoke('test/unknown/probe',{'messages':[]})

if __name__=='__main__':unittest.main()
