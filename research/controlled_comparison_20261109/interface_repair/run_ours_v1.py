"""Run the actual learning-inquiry-v3 controller through a configurable API transport."""
from pathlib import Path
from types import SimpleNamespace
import json,sys,argparse,time,traceback,hashlib,re
from openai import OpenAI
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT/'runtime/ours_source'
sys.path.insert(0,str(PROJECT/'src'))
import learning_lab as lab
from learning_memory import Memory
from discover import read,write
from learning_support import QuestionState,HypothesisState,validate_uptake,audit_review
from hypothesis_cycle import validate_step

ap=argparse.ArgumentParser();ap.add_argument('--case',required=True);ap.add_argument('--phase',default='generation');a=ap.parse_args()
OUT=ROOT/'runs'/a.case/'ours'/a.phase;OUT.mkdir(parents=True,exist_ok=True)
cfg=json.loads((ROOT/'model_config.json').read_text());model=cfg['model']
api=OpenAI(base_url=json.loads((ROOT/'gateway_endpoint.json').read_text())['base_url'],api_key=f'{a.case}/ours/{a.phase}',max_retries=0,timeout=240)
run=OUT/'inquiry';last_stage=None;feedback={}
domains=[('domain_scientist','光学偏振与光计算' if a.case=='optical' else '主动机械超材料与非平衡动力学'),('theory_scientist','统计物理、随机过程与可辨识性')]
lab.CASES[a.case]=domains
class Frozen(Exception):pass

def complete(messages,maximum=4500):
 for i in range(3):
  try:return api.chat.completions.create(model=model,messages=messages,max_tokens=maximum).choices[0].message.content
  except Exception as e:
   if i==2 or not any(t in str(e) for t in ['Connection error','timed out']):raise
   time.sleep(2)

def parse(text):
 text=text.strip()
 if text.startswith('```'):text=text.split('\n',1)[1].rsplit('```',1)[0]
 try:return json.loads(text)
 except json.JSONDecodeError:
  value,end=json.JSONDecoder().raw_decode(text)
  if not isinstance(value,dict) or not re.fullmatch(r'[}\s]+',text[end:]):raise
  value['transport_format_recovery']={'rule':'Discard trailing extra closing braces after one complete JSON object','discarded':text[end:],'scientific_fields_changed':False}
  return value

def stage_run(run,sid,role,prompt,inputs,model,effort,timeout):
 global last_stage
 if sid=='07_check':raise Frozen()
 last_stage=sid
 workspace=run/'stages'/sid/'api/workspace';workspace.mkdir(parents=True,exist_ok=True)
 target=workspace/'result.json'
 if target.exists() and sid not in feedback:return target,read(target)
 previous=sorted(workspace.glob('response_*.txt'))
 if not target.exists() and previous and sid not in feedback:
  recovered=parse(previous[-1].read_text())
  if 'transport_format_recovery' in recovered:
   write(target,recovered);return target,recovered
 records=[{'path':str(p),'text':p.read_text()} for p in inputs]
 common='All file contents accessible to you are embedded below. Use ONLY this supplied corpus; external search is disabled identically for all systems. The source paper identity is visible. Return one JSON object only, with the requested fields and summary(string), artifacts(array), evidence(array), claims(array), limitations(array), next_actions(array). Put requested markdown artifact contents in an additional files object {"NOTE.md":"text"}; the transport writes it verbatim. Do not invent files or reading. For source local_path use this actual dossier path: '+str(PROJECT/'case_data'/a.case/'dossier.json')+'. An independent foundation is unavailable in this fixed corpus; report the gap. Be concise; preserve all exact IDs and quotes required by the protocol. '
 if a.case=='optical':
  common += ' Transport constraints: keep the whole JSON concise, about 1800 tokens, and avoid repeating scientific paragraphs in files. The closed corpus cannot fulfill external searches: preserve unavailable knowledge as remaining_gap rather than requesting that unavailable service. source_use must cover exactly the sources array in broker replies, not the common dossier source catalog; if broker sources is empty, source_use=[]. Whenever a learning request is needed, copy development_step.gap and reason verbatim. '
 messages=[{'role':'system','content':common+'\n'+prompt},{'role':'user','content':json.dumps(records,ensure_ascii=False)}]
 if sid in feedback:messages.extend(feedback[sid])
 raw=complete(messages,5000)
 attempt=len(list(workspace.glob('response_*.txt')))
 (workspace/f'response_{attempt}.txt').write_text(raw)
 result=parse(raw)
 # Persist only model-authored artifacts; no controller scientific repairs.
 for name,body in result.pop('files',{}).items():
  path=(workspace/name).resolve()
  if path.is_relative_to(workspace.resolve()) and isinstance(body,str):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(body)
 write(target,result)
 return target,result

def no_fetch(url):raise OSError('External retrieval disabled by common-corpus protocol')
lab.stage_run=stage_run
args=SimpleNamespace(model=model,effort='low',timeout=240,check_timeout=240,executor='api',development_periods=0,knowledge_fetch=no_fetch,knowledge_policy={'knowledge_before_exclusive':'2026-11-10','excluded_dois':[],'excluded_titles':[],'retrieval_results_per_query':4,'read_full_text':False})

def generation():
 for retry in range(12):
  try:lab.run_case(a.case,run,args,Memory(OUT/'memory'));return
  except Frozen:return
  except (ValueError,KeyError,TypeError) as e:
   if not last_stage:raise
   result=run/'stages'/last_stage/'api/workspace/result.json'
   folder=result.parent;raws=sorted(folder.glob('response_*.txt'))
   if len(raws)>=3:raise
   prev=result.read_text() if result.exists() else (raws[-1].read_text() if raws else '')
   correction={'error':str(e),'stage':last_stage,'scope':'schema/provenance validation only; no scientific answer supplied'}
   (folder/f'validation_{len(raws)}.json').write_text(json.dumps(correction,indent=2))
   feedback.setdefault(last_stage,[]).extend([{'role':'assistant','content':prev},{'role':'user','content':'Controller validation failed: '+str(e)+'. Return the complete corrected JSON, keeping scientific content unless required by the validation.'}])
   print('schema recovery',last_stage,str(e),flush=True)
 raise RuntimeError('Recovery budget exhausted')

def correction():
 dossier=(ROOT/'cases'/a.case/'dossier.json').read_text();packet=(ROOT/'cases'/a.case/'correction_packet.json').read_text()
 initial=complete([{'role':'system','content':'You are the domain researcher. Audit every numbered claim against supplied evidence. Return item-level correct/incorrect/unsupported judgments, corrected quantities and implications. Do not reject unproved hypotheses merely for lack of proof.'},{'role':'user','content':dossier+'\n'+packet}],2200)
 review=complete([{'role':'system','content':lab.REVIEW_PROTOCOL+' For this stand-alone audit, use plain item-level prose; inspect specific arithmetic, logical and attribution errors, including false positives. No external sources.'},{'role':'user','content':dossier+'\n'+packet+'\nResearcher audit:\n'+initial}],1800)
 final=complete([{'role':'system','content':'Return as the original author. Respond to the specific reviewer findings. Save a final item-by-item audit with corrected quantities and implications; keep correct control statements.'},{'role':'user','content':dossier+'\n'+packet+'\nInitial:\n'+initial+'\nReview:\n'+review}],2200)
 write(OUT/'result.json',{'initial':initial,'review':review,'final':final})

start=time.monotonic()
try:
 if a.phase=='generation':
  generation();write(OUT/'result.json',{'final':read(run/'ideas.json')});status={'status':'complete'}
 else:correction();status={'status':'complete'}
except BaseException as e:status={'status':'budget_exhausted' if 'BUDGET_EXHAUSTED' in str(e) else 'failed','error':str(e),'traceback':traceback.format_exc()}
status.update(seconds=time.monotonic()-start,scope='Actual learning-inquiry-v3 controller; API/file transport, common fixed corpus, fresh memory, no extra portfolio period; separate author-review-uptake audit')
write(OUT/'STATUS.json',status);print(a.case,'ours',a.phase,status['status'],flush=True)
