"""Official EvoScientist application, isolated case state and common model gateway."""
from pathlib import Path
import argparse, os, sys, json, time, traceback, importlib, shutil

ROOT=Path(__file__).resolve().parents[1]
raise RuntimeError('Historical research lock: unscreened native shell tools are disabled; use the screened API pipeline')
ap=argparse.ArgumentParser();ap.add_argument('--case',required=True);ap.add_argument('--phase',default='generation');a=ap.parse_args()
OUT=ROOT/'runs'/a.case/'evoscientist'/a.phase;OUT.mkdir(parents=True,exist_ok=True)
for key,folder in [('WORKSPACE','workspace'),('MEMORY','memory'),('SKILLS','skills'),('RUNS','sessions')]:
 p=OUT/folder;p.mkdir(exist_ok=True);os.environ['EVOSCIENTIST_'+key+'_DIR']=str(p)
WORK=OUT/'workspace'
UP=next((ROOT.parent/'replication_selection_20261108/execution/upstream').glob('EvoScientist-*'))
sys.path.insert(0,str(UP))

def main():
 from langchain_openai import ChatOpenAI
 from langchain_core.messages import HumanMessage
 from EvoScientist.config import EvoScientistConfig
 evo=importlib.import_module('EvoScientist.EvoScientist')
 cfg=json.loads((ROOT/'model_config.json').read_text())
 evo._chat_model=ChatOpenAI(model=cfg['model'],api_key=f'{a.case}/evoscientist/{a.phase}',base_url=json.loads((ROOT/'gateway_endpoint.json').read_text())['base_url'],max_tokens=2600,timeout=240,max_retries=0,use_responses_api=False)
 config=EvoScientistConfig(provider='openai',model=cfg['model'],auto_approve=True,enable_ask_user=False)
 for name in ['dossier.json','measurements.csv','correction_packet.json']:
  if name=='correction_packet.json' and a.phase!='correction':continue
  shutil.copy2(ROOT/'cases'/a.case/name,WORK/name)
 restrictions='Use only /dossier.json and /measurements.csv as scientific evidence. External browsing and downloads are disabled for all systems. CPU only; at most 4 threads and 120 seconds per computation, no training or synthetic replacement data. Do not claim novel discovery from the visible source paper. Keep unproved hypotheses and alternatives. '
 if a.phase=='correction':
  prompts=[restrictions+'The complete dossier and audit are provided inline: '+(WORK/'dossier.json').read_text()+'\n'+(WORK/'correction_packet.json').read_text()+'\nThis is a compact audit; answer directly without delegation, planning tools or memory extraction. Audit /correction_packet.json item by item. State correct/incorrect/unsupported, corrected calculations and consequences. Recompute from the CSV if needed. Save /audit.md and return your complete answer. At most 12 tool calls.']
 else:
  prompts=[restrictions+'Develop substantive explanatory hypotheses and conditional consequences beyond the supplied study. Use your native planning, research, analysis and critique tools as helpful. At most 24 tool calls. Save /ideas.md and a reusable research note under /memory/. Return concrete questions, competing explanations and what the measurements can and cannot establish.',
   restrictions+'Continue from /ideas.md and your saved memory in this fresh session. Develop a distinct alternative or revise a premise using a concrete derivation or analysis; evaluate which predictions distinguish it. Preserve unresolved branches. At most 16 tool calls. Save /final.md and return all final questions and hypotheses with actual evidence and unresolved assumptions.']
 finals=[]
 for i,prompt in enumerate(prompts):
  target=OUT/f'session_{i}.json'
  if target.exists():finals.append(json.loads(target.read_text())['final']);continue
  agent=evo.create_cli_agent(workspace_dir=str(WORK),config=config)
  state=agent.invoke({'messages':[HumanMessage(content=prompt)]},config={'configurable':{'thread_id':f'{a.case}_{a.phase}_{i}'},'recursion_limit':70})
  final=state['messages'][-1].content
  target.write_text(json.dumps({'messages':[m.model_dump() for m in state['messages']],'final':final},ensure_ascii=False,indent=2,default=str));finals.append(final)
 (OUT/'result.json').write_text(json.dumps({'final':finals},ensure_ascii=False,indent=2))

start=time.monotonic()
try:main();status={'status':'complete'}
except Exception as e:status={'status':'budget_exhausted' if 'BUDGET_EXHAUSTED' in str(e) else 'failed','error':str(e),'traceback':traceback.format_exc()}
status.update(seconds=time.monotonic()-start,scope='Official application with isolated memory and bounded common-source task; not paper benchmark reproduction')
(OUT/'STATUS.json').write_text(json.dumps(status,indent=2));print(a.case,'evoscientist',a.phase,status['status'],flush=True)
