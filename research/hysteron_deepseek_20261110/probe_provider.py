"""Minimal official-endpoint thinking/tool probe; never output credentials."""
from pathlib import Path
import json
from openai import OpenAI
R=Path(__file__).resolve().parent
cfg=json.loads((R/'model_config.json').read_text())
k=Path(cfg['credential_file'])
assert not k.stat().st_mode & 0o077
client=OpenAI(api_key=k.read_text().strip(),base_url='https://api.deepseek.com',timeout=180,max_retries=0)
models=client.models.list().model_dump()
(R/'PROVIDER_MODELS.json').write_text(json.dumps(models,indent=2))
r=client.chat.completions.create(model='deepseek-flash',messages=[{'role':'user','content':'Use save_probe to report the integer result of 3*7.'}],tools=[{'type':'function','function':{'name':'save_probe','description':'Save a probe result','parameters':{'type':'object','properties':{'value':{'type':'integer'}},'required':['value']}}}],max_tokens=2048,reasoning_effort='high',extra_body={'thinking':{'type':'enabled'}})
(R/'PROVIDER_PROBE.json').write_text(r.model_dump_json(indent=2))
m=r.choices[0].message
assert m.tool_calls and json.loads(m.tool_calls[0].function.arguments)['value']==21
r2=client.chat.completions.create(model='deepseek-flash',messages=[{'role':'user','content':'Use save_probe to report the integer result of 3*7.'},m.model_dump(exclude_none=True),{'role':'tool','tool_call_id':m.tool_calls[0].id,'content':'Saved 21. Reply done.'}],max_tokens=2048,reasoning_effort='high',extra_body={'thinking':{'type':'enabled'}})
(R/'PROVIDER_TOOL_CONTINUATION.json').write_text(r2.model_dump_json(indent=2))
print(json.dumps({'model':r.model,'thinking_present':bool(getattr(m,'reasoning_content',None)),'tool_result':21,'continuation':r2.choices[0].finish_reason,'models':models}))
