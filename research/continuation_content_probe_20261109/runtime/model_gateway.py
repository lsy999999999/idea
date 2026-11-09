"""One configurable model transport and per-system usage ledger. No keys in artifacts."""
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import json,os,time,threading,re,tomllib,hashlib,sys
from openai import OpenAI
import tiktoken
ROOT=Path(__file__).resolve().parents[1]
CFG=json.loads((ROOT/'model_config.json').read_text())
locks={};master=threading.Lock()
provider_slots=threading.BoundedSemaphore(2)
encoding=tiktoken.get_encoding('o200k_base')

def estimate_tokens(payload):
    # A measured-token proxy, not bytes. Exact billing comes from response usage.
    return int(len(encoding.encode(json.dumps(payload,ensure_ascii=False)))*1.1)+256

def transport_identity():
    fields={k:CFG.get(k) for k in ['model','api_style','reasoning_effort','base_url','credential_source','api_key_env','preserve_reasoning_items','chat_reasoning_parameter']}
    if CFG.get('credential_source')=='existing_codex_config':
        config=tomllib.loads(Path('/Users/LSY/.codex/config.toml').read_text())
        fields['effective_base_url']=config['model_providers'][config['model_provider']]['base_url']
    return hashlib.sha256(json.dumps(fields,sort_keys=True).encode()).hexdigest()

def client():
    if CFG['credential_source']=='existing_codex_config':
        c=tomllib.loads(Path('/Users/LSY/.codex/config.toml').read_text())
        a=json.loads(Path('/Users/LSY/.codex/auth.json').read_text())
        return OpenAI(api_key=a['OPENAI_API_KEY'],base_url=c['model_providers'][c['model_provider']]['base_url'],timeout=180,max_retries=0)
    return OpenAI(api_key=os.environ[CFG['api_key_env']],base_url=CFG['base_url'],timeout=180,max_retries=0)

def responses_input(messages):
    out=[]
    for m in messages:
        if m.get('provider_response_items'):
            if m['role'] != 'assistant':
                raise ValueError('Provider response items belong only to assistant messages')
            # SDK Python field names (async_) are not wire-format names.
            out.extend({('async' if k=='async_' else k):v for k,v in item.items() if v is not None}
                       for item in m['provider_response_items'])
            continue
        if m['role']=='tool':
            out.append({'type':'function_call_output','call_id':m['tool_call_id'],'output':m.get('content','')});continue
        if m.get('content'):
            out.append({'role':m['role'],'content':m['content']})
        for tc in m.get('tool_calls',[]):
            out.append({'type':'function_call','call_id':tc['id'],'name':tc['function']['name'],'arguments':tc['function']['arguments']})
    if not any(m.get('role')=='user' for m in out):out.append({'role':'user','content':'Follow the instructions.'})
    return out

def invoke(group,payload):
    if not re.fullmatch(r'[a-z0-9_]+/[a-z0-9_]+/(generation|correction|evaluation|probe)',group):raise ValueError('Invalid run account')
    with master:lock=locks.setdefault(group,threading.Lock())
    with lock:
        folder=ROOT/'runs'/group;folder.mkdir(parents=True,exist_ok=True)
        if (folder/'FINAL_FREEZE.json').exists() or (folder/'GENERATION_FREEZE.json').exists():
            raise ValueError('Frozen account; create a fresh run instead of rewriting prior results')
        ledger_path=folder/'usage.json'
        ledger=json.loads(ledger_path.read_text()) if ledger_path.exists() else {'calls':0,'input_tokens':0,'output_tokens':0,'cached_tokens':0,'reasoning_tokens':0,'failed_calls':0,'usage_unknown_calls':0,'wall_model_seconds':0}
        if ledger.get('requested_model',CFG['model']) != CFG['model']:
            raise ValueError('Model changed in an existing account; use prepare_replay.py for a fresh experiment')
        identity=transport_identity()
        if ledger.get('transport_identity',identity)!=identity:
            raise ValueError('Provider or transport settings changed; use a fresh experiment account')
        limit=CFG['budgets'][group.split('/')[-1]]
        # Exact saved-response replay for interrupted runs; no hidden new inference.
        for previous in folder.glob('*.request.json'):
            old=json.loads(previous.read_text())
            cached=previous.with_name(previous.name.replace('.request.json','.chat.json'))
            if old.get('payload') == payload and cached.exists():
                with (folder/'replays.jsonl').open('a') as log:log.write(json.dumps({'request':previous.name,'time':time.time()})+'\n')
                return json.loads(cached.read_text())
        estimate=estimate_tokens(payload)
        maxout=min(int(payload.get('max_completion_tokens') or payload.get('max_tokens') or 2000),limit['output_tokens']-ledger['output_tokens']-ledger.get('unknown_output_reserve',0))
        if ledger['calls']>=limit['calls'] or maxout<300 or ledger['input_tokens']+ledger.get('unknown_input_reserve',0)+estimate>limit['input_tokens']:
            raise RuntimeError('BUDGET_EXHAUSTED')
        ledger['calls']+=1; idx=ledger['calls']; prefix=folder/f'{idx:03d}'
        req={'requested_model':CFG['model'],'reasoning_effort':CFG.get('reasoning_effort'),'api_style':CFG['api_style'],'payload':payload,'estimated_input_tokens':estimate,'input_estimator':'o200k_base + 10% + 256; actual usage settles ledger','max_output_tokens':maxout}
        prefix.with_suffix('.request.json').write_text(json.dumps(req,ensure_ascii=False,indent=2))
        start=time.monotonic()
        try:
            provider_slots.acquire()
            api=client()
            if CFG['api_style']=='responses':
                kwargs={'model':CFG['model'],'input':responses_input(payload['messages']),'max_output_tokens':maxout,'store':False}
                if CFG.get('reasoning_effort'):kwargs['reasoning']={'effort':CFG['reasoning_effort']}
                if CFG.get('preserve_reasoning_items',False):kwargs['include']=['reasoning.encrypted_content']
                fmt=payload.get('response_format')
                if fmt:
                    kwargs['text']={'format':({'type':'json_schema',**fmt['json_schema']} if fmt['type']=='json_schema' else fmt)}
                if payload.get('tools'):
                    kwargs['tools']=[{'type':'function','strict':False,**t['function']} for t in payload['tools']]
                    if 'parallel_tool_calls' in payload:kwargs['parallel_tool_calls']=payload['parallel_tool_calls']
                    if payload.get('tool_choice'):
                        choice=payload['tool_choice'];kwargs['tool_choice']=({'type':'function','name':choice['function']['name']} if isinstance(choice,dict) else choice)
                r=api.responses.create(**kwargs);raw=r.model_dump(by_alias=True,exclude_none=True);u=raw.get('usage') or {}
                calls=[{'id':x.call_id,'type':'function','function':{'name':x.name,'arguments':x.arguments}} for x in r.output if x.type=='function_call']
                response={'id':r.id,'object':'chat.completion','created':int(time.time()),'model':raw.get('model',CFG['model']),'choices':[{'index':0,'message':{'role':'assistant','content':r.output_text or None,'tool_calls':calls or None},'finish_reason':'tool_calls' if calls else ('length' if raw.get('status')=='incomplete' else 'stop')}],'usage':{'prompt_tokens':u.get('input_tokens',0),'completion_tokens':u.get('output_tokens',0),'total_tokens':u.get('total_tokens',0),'prompt_tokens_details':u.get('input_tokens_details',{}),'completion_tokens_details':u.get('output_tokens_details',{})}}
                response['choices'][0]['message']['provider_response_items']=raw.get('output',[])
                if not u:response['usage']=None
            else:
                kwargs={k:v for k,v in payload.items() if k in {'messages','tools','tool_choice','response_format','parallel_tool_calls'}}
                kwargs['messages']=[{k:v for k,v in m.items() if k!='provider_response_items'} for m in kwargs['messages']]
                if CFG.get('reasoning_effort') and CFG.get('chat_reasoning_parameter'):
                    kwargs[CFG['chat_reasoning_parameter']]=CFG['reasoning_effort']
                r=api.chat.completions.create(model=CFG['model'],max_tokens=maxout,**kwargs);raw=r.model_dump();response=raw
            prefix.with_suffix('.response.json').write_text(json.dumps(raw,ensure_ascii=False,indent=2))
            prefix.with_suffix('.chat.json').write_text(json.dumps(response,ensure_ascii=False,indent=2))
            u=response.get('usage') or {}
            if not u:
                ledger['usage_unknown_calls']+=1
                ledger['unknown_input_reserve']=ledger.get('unknown_input_reserve',0)+estimate
                ledger['unknown_output_reserve']=ledger.get('unknown_output_reserve',0)+maxout
            ledger['input_tokens']+=u.get('prompt_tokens',0)
            ledger['output_tokens']+=u.get('completion_tokens',0)
            ledger['cached_tokens']+=(u.get('prompt_tokens_details') or {}).get('cached_tokens',0)
            ledger['reasoning_tokens']+=(u.get('completion_tokens_details') or {}).get('reasoning_tokens',0)
            return response
        except Exception as e:
            ledger['failed_calls']+=1;ledger['usage_unknown_calls']+=1
            ledger['unknown_input_reserve']=ledger.get('unknown_input_reserve',0)+estimate
            ledger['unknown_output_reserve']=ledger.get('unknown_output_reserve',0)+maxout
            prefix.with_suffix('.error.json').write_text(json.dumps({'type':type(e).__name__,'message':str(e)},indent=2))
            raise
        finally:
            provider_slots.release()
            ledger['wall_model_seconds']+=time.monotonic()-start
            ledger['requested_model']=CFG['model'];ledger['limits']=limit
            ledger['transport_identity']=identity
            ledger_path.write_text(json.dumps(ledger,indent=2))
            print(group,idx,ledger['input_tokens'],ledger['output_tokens'],flush=True)

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_POST(self):
        if self.path not in ['/v1/chat/completions','/chat/completions']:
            self.send_error(404);return
        try:
            group=self.headers.get('Authorization','').removeprefix('Bearer ')
            payload=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            result=invoke(group,payload);code=200
        except Exception as e:
            code=429 if 'BUDGET_EXHAUSTED' in str(e) else 500
            result={'error':{'message':str(e),'type':type(e).__name__,'code':'budget_exhausted' if code==429 else 'model_error'}}
        raw=json.dumps(result,ensure_ascii=False).encode();self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
if __name__=='__main__':
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    (ROOT/'gateway_endpoint.json').write_text(json.dumps({'base_url':f'http://127.0.0.1:{server.server_port}/v1','pid':os.getpid()}))
    print('Gateway ready',server.server_port,flush=True);server.serve_forever()
