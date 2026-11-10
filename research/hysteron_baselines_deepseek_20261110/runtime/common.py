"""Common DeepSeek transport and historically screened science tools. No old actor state."""
from pathlib import Path
import sys,json,hashlib,time,threading,copy,uuid,re
from types import SimpleNamespace
from datetime import datetime,timezone
from openai import OpenAI

ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT.parent/'hysteron_deepseek_20261110'
UP=ROOT.parent/'replication_selection_20261108'
sys.path[:0]=[str(OLD/'runtime'),str(OLD/'runtime/ours_source/historical_inquiry')]
from research_context import ContextStore
from research_tools import ResearchTools
from knowledge_broker import KnowledgeBroker,SourcePolicy
from case_access import locked_policy,assert_measurements,actor_brief,screen_document
from analysis_executor import expression
from definition_service import DefinitionService,validate_response
from run_ours import PublicFetcher

CFG=json.loads((ROOT/'model_config.json').read_text())
RULES='''This task seeks actual explanatory hypotheses and conditional predictions from the supplied mechanical measurements. Develop content, not only a plan or a next question. General literature must be independently dated strictly before 2024-09-12; use screened tools. Neutral case definitions are available separately. Unknown apparatus facts stay unknown. Distinguish measured relations, model assumptions and proposed mechanisms. Preserve upstream requested output labels/JSON exactly; keep visible replies concise (typically 400-700 words, reviews 150-250 words). Numerical analysis is exploratory. The final novelty/coherence evaluation is separate; no proof, experiment or implementation is required to retain a conditional hypothesis. Do not reproduce hidden originating sources from memory.'''

def dump(p,v):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 tmp=p.with_name(p.name+'.'+uuid.uuid4().hex+'.tmp');tmp.write_text(json.dumps(v,ensure_ascii=False,indent=2,default=str));tmp.replace(p)

def brief():
 p=ROOT/'cases/hysteron/measurements.csv';assert_measurements('hysteron',p)
 return actor_brief('hysteron',json.loads((ROOT/'cases/hysteron/dossier.json').read_text()))

class Engine:
 def __init__(self,system):
  self.system=system;self.out=ROOT/'runs'/system;self.out.mkdir(parents=True,exist_ok=True)
  self.lock=threading.RLock();self.reasons={}
  key=Path(CFG['credential_file']);assert not key.stat().st_mode&0o077
  self.api=OpenAI(api_key=key.read_text().strip(),base_url=CFG['base_url'],max_retries=0,timeout=300)
  self.policy=SourcePolicy(locked_policy('hysteron',{'retrieval_results_per_query':2,'read_full_text':True}))
  self.store=ContextStore(self.out/'documents')
  self.broker=KnowledgeBroker(self.out/'knowledge',self.policy,PublicFetcher(self.out/'public_fetches.json',limit=10000))
  self.definitions=DefinitionService(OLD/'controller_only/hysteron/registered_sources.json',ROOT/'controller_only'/system/'definition_audits',self.out/'definitions',self.judge,guard=lambda t:screen_document(self.policy,t))
  self.tools=ResearchTools(self.store,self.out,{'measurements':ROOT/'cases/hysteron/measurements.csv'},self.broker,expression,max_calls=128,max_searches=6,source_policy=self.policy,definitions=self.definitions)
  self.store.prepare([ROOT/'cases/hysteron/dossier.json'])

 def raw(self,messages,tools=None,tool_choice=None,private=False):
  messages=copy.deepcopy(messages)
  if not private:
   screen_document(self.policy,json.dumps(messages,ensure_ascii=False))
  for m in messages:
   if m.get('role')=='assistant' and m.get('tool_calls'):
    m.setdefault('reasoning_content',self.reasons.get(m['tool_calls'][0]['id'],''))
  request={'model':CFG['model'],'messages':messages,'max_tokens':CFG['max_completion_tokens'],'reasoning_effort':CFG['reasoning_effort'],'extra_body':{'thinking':{'type':'enabled'}}}
  if tools:request['tools']=tools
  # DeepSeek thinking accepts automatic tools but rejects forced named/required tools.
  if tool_choice in ('auto','none'):request['tool_choice']=tool_choice
  identity=hashlib.sha256(json.dumps(request,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
  folder=(ROOT/'controller_only'/self.system/'calls') if private else self.out/'calls'
  target=folder/(identity+'.json')
  if target.exists():
   saved=json.loads(target.read_text());result=saved['response']
   from openai.types.chat import ChatCompletion
   response=ChatCompletion.model_validate(result)
   self.remember(response);return response
  attempt_start=len(list(folder.glob(identity+'.attempt*.json')))
  for attempt in range(8):
   started=time.monotonic();attempt_path=folder/(identity+f'.attempt{attempt_start+attempt}.json')
   # Failed/truncated attempts remain auditable. Successful calls are content-addressed.
   try:
    response=self.api.chat.completions.create(**request)
    payload={'request':request,'response':response.model_dump(),'seconds':time.monotonic()-started,'at':datetime.now(timezone.utc).isoformat(),'system':self.system,'private_service':private}
    dump(attempt_path,payload)
    self.usage(payload)
    if response.choices[0].finish_reason=='length':
     request['max_tokens']=min(131072,max(CFG['truncation_recovery_tokens'],request['max_tokens']*2))
     continue
    m=response.choices[0].message
    if not m.content and not m.tool_calls:raise ValueError('Empty completed model response')
    dump(target,payload);self.remember(response)
    print(json.dumps({'system':self.system,'call':identity[:12],'tokens':response.usage.total_tokens,'finish':response.choices[0].finish_reason}),flush=True)
    return response
   except Exception as e:
    dump(attempt_path,{'error_type':type(e).__name__,'error':str(e),'request':request,'seconds':time.monotonic()-started})
    if attempt==7:raise
    time.sleep(min(3*(attempt+1),20))
  raise RuntimeError('Response still truncated after recovery')

 def remember(self,r):
  m=r.choices[0].message
  for t in m.tool_calls or []:self.reasons[t.id]=getattr(m,'reasoning_content','') or ''

 def usage(self,payload):
  u=payload['response'].get('usage') or {}
  row={'at':payload['at'],'private_service':payload['private_service'],'usage':u,'seconds':payload['seconds']}
  with self.lock:
   with (self.out/'usage.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')

 def science_call(self,name,args,call_id):
  with self.lock:return self.tools.call(name,args,call_id)

 def run(self,messages,function=None,max_tool_turns=2,private=False):
  msgs=copy.deepcopy(messages)
  if not private:msgs.insert(0,{'role':'system','content':RULES+'\nDataset ID: measurements. All 123 rows are supplied in the common dossier. Tools can compute on the complete CSV.'})
  offered=[] if private else self.tools.definitions
  if function:
   offered=[{'type':'function','function':function}]
   msgs.append({'role':'user','content':'Return your completed result by calling '+function['name']+' with its required arguments. If a function call is unavailable, return the same complete JSON object.'})
  for step in range(max_tool_turns+1):
   # Leave a completion opportunity after bounded tool use, rather than raising on budget.
   active=offered if step<max_tool_turns or function else None
   if not active and step:msgs.append({'role':'user','content':'Now deliver your substantive result using the available evidence; preserve unknowns. Do not request more tools.'})
   r=self.raw(msgs,active,{'type':'function','function':{'name':function['name']}} if function else None,private)
   m=r.choices[0].message
   if function:
    try:
     if m.tool_calls:return json.loads(m.tool_calls[0].function.arguments)
     content=(m.content or '').strip()
     if content.startswith('```'):content=content.split('\n',1)[1].rsplit('```',1)[0]
     return json.loads(content)
    except (ValueError,TypeError):
     msgs.append({'role':'user','content':'The previous reply did not provide the required structured result. Call '+function['name']+' now with the complete result.'})
     continue
   if not m.tool_calls:return r
   msgs.append(m.model_dump(exclude_none=True))
   for t in m.tool_calls:
    try:result=self.science_call(t.function.name,json.loads(t.function.arguments),t.id)
    except Exception as e:result={'status':'error','message':str(e)}
    msgs.append({'role':'tool','tool_call_id':t.id,'content':json.dumps(result,ensure_ascii=False)})
  raise RuntimeError('No final response')

 def judge(self,role,instruction,payload):
  for attempt in range(3):
   r=self.raw([{'role':'system','content':instruction+' Return JSON only.'},{'role':'user','content':json.dumps(payload,ensure_ascii=False)}],private=True)
   text=r.choices[0].message.content.strip()
   if text.startswith('```'):text=text.split('\n',1)[1].rsplit('```',1)[0]
   try:
    value=json.loads(text);validate_response(role,value,payload);return value
   except (ValueError,TypeError,KeyError):
    if attempt==2:raise

class Proxy:
 def __init__(self,engine):self.engine=engine;self.chat=SimpleNamespace(completions=SimpleNamespace(create=self.create))
 def create(self,model,messages,**kwargs):return self.engine.run(messages)
 def call(self,messages,**kwargs):
  text=self.engine.run(messages).choices[0].message.content
  # Upstream ResearchAgent regex requires literal headings; retain raw API bytes.
  normalized=re.sub(r'(?m)^\s*#{1,6}\s*','',text.replace('**',''))
  normalized=re.sub(r'(?mi)^(Problem|Method|Experiment|Rationale|Review|Feedback|Rating)(?:\s*\([^\n)]*\))?\s*[:.：—-]\s*',lambda m:m.group(1)+': ',normalized)
  digest=hashlib.sha256(text.encode()).hexdigest()
  dump(self.engine.out/'format_adaptations'/(digest+'.json'),{'raw':text,'normalized':normalized,'scope':'Markdown/heading syntax only; scientific content preserved'})
  return normalized

def finalize(engine,trajectory):
 p=engine.out/'FINAL.json'
 if p.exists():return json.loads(p.read_text())
 contract={'name':'save_hypotheses','description':'Record the concrete final hypotheses from the actual system trajectory.','parameters':{'type':'object','properties':{'hypotheses':{'type':'array','items':{'type':'object','properties':{'id':{'type':'string'},'title':{'type':'string'},'mechanism':{'type':'string'},'equations_or_derivation':{'type':'string'},'measured_support':{'type':'string'},'assumptions':{'type':'array','items':{'type':'string'}},'distinct_prediction':{'type':'string'},'alternatives':{'type':'string'},'trajectory_origin':{'type':'string'}},'required':['id','title','mechanism','equations_or_derivation','measured_support','assumptions','distinct_prediction','alternatives','trajectory_origin']}},'summary':{'type':'string'}},'required':['hypotheses','summary']}}
 result=engine.run([{'role':'system','content':'Extract 1-3 substantive hypotheses actually developed in this system trajectory. Retain conditional/unvalidated ones. Do not invent a stronger new mechanism at this reporting stage. Cite actual trajectory positions. Chinese prose; equations can use ASCII. A mere plan does not become a hypothesis.'},{'role':'user','content':json.dumps(trajectory,ensure_ascii=False)}],function=contract)
 if not result.get('hypotheses'):raise ValueError('No hypothesis extracted; research continuation required')
 dump(p,result);return result
