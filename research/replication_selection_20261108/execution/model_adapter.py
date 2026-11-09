"""Responses transport for unchanged upstream prompts; no credentials in artifacts."""
from pathlib import Path
from types import SimpleNamespace
import json
import threading
import time
import tomllib
from openai import OpenAI

ROOT = Path(__file__).resolve().parent
MODEL = 'gpt-6-luna'
_lock = threading.Lock()
_counter = 0

def provider():
    cfg = tomllib.loads(Path('/Users/LSY/.codex/config.toml').read_text())
    auth = json.loads(Path('/Users/LSY/.codex/auth.json').read_text())
    return OpenAI(api_key=auth['OPENAI_API_KEY'],
                  base_url=cfg['model_providers'][cfg['model_provider']]['base_url'],
                  timeout=150, max_retries=1)

def complete(messages, group='shared', max_tokens=2400, function=None):
    global _counter
    with _lock:
        _counter += 1
        index = _counter
    folder = ROOT/'runs'/group/'calls'
    folder.mkdir(parents=True, exist_ok=True)
    prefix = folder/f'{index:03d}_{time.time_ns()}'
    messages = list(messages)
    if not any(m.get('role')=='user' for m in messages):
        messages.append({'role':'user','content':'Please follow the instructions.'})
    request = {'model': MODEL, 'messages': messages, 'max_output_tokens': max_tokens,
               'reasoning_effort': 'low', 'function': function,
               'transport_note': 'Responses API; upstream temperature unsupported and omitted.'}
    prefix.with_suffix('.request.json').write_text(json.dumps(request,ensure_ascii=False,indent=2))
    kwargs = dict(model=MODEL,input=messages,reasoning={'effort':'low'},
                  max_output_tokens=max_tokens,store=False)
    if function:
        kwargs['tools'] = [dict(type='function',name=function['name'],
                                description=function.get('description',''),
                                parameters=function['json_schema'],strict=False)]
        kwargs['tool_choice'] = {'type':'function','name':function['name']}
    start = time.time()
    try:
        response = provider().responses.create(**kwargs)
        raw = response.model_dump()
        prefix.with_suffix('.response.json').write_text(json.dumps(raw,ensure_ascii=False,indent=2))
        if function:
            calls = [o for o in response.output if o.type == 'function_call']
            if not calls:
                raise RuntimeError('Missing required function call')
            result = json.loads(calls[0].arguments)
        else:
            result = response.output_text
            if not result:
                raise RuntimeError('Empty model output')
        print(f'{group}: call {index} complete in {time.time()-start:.1f}s',flush=True)
        return result
    except Exception as exc:
        prefix.with_suffix('.error.json').write_text(json.dumps({'type':type(exc).__name__,'message':str(exc),'seconds':time.time()-start},indent=2))
        raise

class ResearchClient:
    def call(self,messages,**kwargs):
        return complete(messages,'researchagent',max_tokens=1400)

class ChatClient:
    def __init__(self, group='virtual_lab'):
        self.group=group
        self.chat=SimpleNamespace(completions=SimpleNamespace(create=self.create))
    def create(self,model,messages,**kwargs):
        text=complete(messages,self.group,max_tokens=kwargs.get('max_tokens') or 2600)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text,tool_calls=None))])
