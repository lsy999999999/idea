"""Official AI Scientist-v2 ideation and bounded implementation/improvement/debug nodes."""
from pathlib import Path
import json,os,sys,time,traceback,uuid,argparse,random
ROOT=Path(__file__).resolve().parent
MODEL=json.loads((ROOT/'model_config.json').read_text())['model']
ap=argparse.ArgumentParser();ap.add_argument('--case',required=True);ap.add_argument('--phase',default='generation');a=ap.parse_args()
OUT=ROOT/'runs'/a.case/'scientist_v2'/a.phase;OUT.mkdir(parents=True,exist_ok=True)
QUEUE=ROOT/'requests';QUEUE.mkdir(exist_ok=True)
UP=next(Path('/home/lsy/ideas_replication_20261108/upstream').glob('AI-Scientist-v2-*'));sys.path.insert(0,str(UP))

def request(messages,max_tokens=3000,function=None):
 uid=uuid.uuid4().hex;target=QUEUE/(uid+'.request.json')
 payload={'group':f'{a.case}/scientist_v2/{a.phase}','messages':messages,'max_tokens':max_tokens,'function':function}
 target.write_text(json.dumps(payload));answer=QUEUE/(uid+'.answer.json');start=time.monotonic()
 while not answer.exists():
  if time.monotonic()-start>300:raise TimeoutError('Model bridge timeout')
  time.sleep(.25)
 data=json.loads(answer.read_text())
 if 'error' in data:raise RuntimeError(data['error'])
 return data['result']

def response_from_llm(prompt,client,model,system_message,msg_history=None,**kwargs):
 history=(msg_history or [])+[{'role':'user','content':prompt}]
 text=request([{'role':'system','content':system_message}]+history,2800)
 return text,history+[{'role':'assistant','content':text}]

def tree_query(system_message=None,user_message=None,func_spec=None,**kwargs):
 from ai_scientist.treesearch.backend import compile_prompt_to_md
 messages=[]
 if system_message:messages.append({'role':'system','content':compile_prompt_to_md(system_message)})
 if user_message:messages.append({'role':'user','content':compile_prompt_to_md(user_message)})
 function={'name':func_spec.name,'description':func_spec.description,'parameters':func_spec.json_schema} if func_spec else None
 return request(messages,1400 if function else 4000,function)

def main():
 os.environ.update(CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='4',MPLBACKEND='Agg')
 random.seed(42)
 import torch
 torch.set_num_threads(4)
 from ai_scientist import perform_ideation_temp_free as ideation
 from ai_scientist.treesearch import parallel_agent as pa
 from ai_scientist.treesearch.interpreter import Interpreter
 from omegaconf import OmegaConf
 ideation.get_response_from_llm=response_from_llm
 ideation.semantic_scholar_tool.use_tool=lambda query:'External search disabled for every system. Only the supplied corpus is available; literature novelty unresolved.'
 pa.query=tree_query
 dossier=(ROOT/'cases'/a.case/'dossier.json').read_text();work=OUT/'workspace';work.mkdir(exist_ok=True)
 import shutil
 shutil.copy2(ROOT/'cases'/a.case/'measurements.csv',work/'measurements.csv')
 limits='Use the supplied actual measurements.csv in the current working directory. CPU only (4 threads), numpy/pandas/scipy/sklearn/matplotlib/torch available. No external downloads or training. Do not substitute synthetic data for these measurements. Each script <=120 seconds. Source identity is visible; focus on substantive follow-up hypotheses and distinguish predictions from observed facts. '
 if a.phase=='correction':
  task=limits+dossier+'\nAudit every item and compute corrected values, preserving correct controls. Save an item-level audit.json. '+(ROOT/'cases'/a.case/'correction_packet.json').read_text();ideas=[];n_nodes=2
 else:
  workshop=limits+dossier+'\nDevelop one substantive explanatory follow-up hypothesis with alternatives and conditional predictions. The existing source conclusion is not a new finding.'
  ideas_path=OUT/'ideas.json'
  ideas=json.loads(ideas_path.read_text()) if ideas_path.exists() else ideation.generate_temp_free_idea(str(ideas_path),None,MODEL,workshop,max_num_generations=1,num_reflections=5,reload_ideas=False)
  if not ideas:raise RuntimeError('Official ideation did not finalize within five reflections')
  task=limits+dossier+'\nResearch idea: '+json.dumps(ideas[0]);n_nodes=4
 cfg=OmegaConf.load(UP/'bfts_config.yaml');cfg.agent.code.model=MODEL;cfg.agent.feedback.model=MODEL;cfg.agent.num_workers=1
 # Explicit CPU/real-data adaptation overrides the upstream unconditional GPU training boilerplate.
 pa.MinimalAgent._prompt_impl_guideline=property(lambda self:{'Execution requirements':limits,'Output requirements':'Provide complete executable Python code and print actual metrics and evidence. Do not claim unexecuted results.'})
 pa.MinimalAgent._prompt_environment=property(lambda self:{'Available packages':'numpy pandas scipy sklearn matplotlib torch; CPU only'})
 agent=pa.MinimalAgent(task_desc=task,cfg=cfg,evaluation_metrics='actual descriptive relations, fit sensitivity and alternative explanations; for audit item-level corrected values',stage_name='1_initial_implementation')
 interpreter=Interpreter(work,timeout=120,env_vars={'CUDA_VISIBLE_DEVICES':'','OMP_NUM_THREADS':'4'})
 nodes=[];parent=None
 try:
  for i in range(n_nodes):
   if parent is None:node=agent._draft();operation='draft'
   elif parent.is_buggy:node=agent._debug(parent);operation='debug'
   else:
    agent.memory_summary=json.dumps([n['analysis'] for n in nodes]);node=agent._improve(parent);operation='improve'
   (OUT/f'node_{i}.py').write_text(node.code)
   execution=interpreter.run('import os\nworking_dir='+repr(str(work))+'\nos.chdir(working_dir)\n'+node.code)
   record={'index':i,'operation':operation,'plan':node.plan,'exec_time':execution.exec_time,'exc_type':execution.exc_type,'term_out':execution.term_out}
   (OUT/f'execution_{i}.json').write_text(json.dumps(record,default=str,indent=2))
   agent.parse_exec_result(node,execution,str(work));record.update(analysis=node.analysis,is_buggy=node.is_buggy)
   nodes.append(record);(OUT/'nodes.json').write_text(json.dumps(nodes,indent=2,default=str));parent=node
 finally:interpreter.cleanup_session()
 final=request([{'role':'system','content':'Summarize only the supplied actual research trajectory. Preserve final hypotheses/questions, conditional implications, measured support, failures and open alternatives. Audit tasks need every item judgment with values. No invented execution.'},{'role':'user','content':task+'\nExecuted nodes: '+json.dumps(nodes)}],2400)
 (OUT/'result.json').write_text(json.dumps({'ideas':ideas,'nodes':nodes,'final':final},ensure_ascii=False,indent=2))

start=time.monotonic()
try:main();status={'status':'complete'}
except Exception as e:status={'status':'budget_exhausted' if 'BUDGET_EXHAUSTED' in str(e) else 'failed','error':str(e),'traceback':traceback.format_exc()}
status.update(seconds=time.monotonic()-start,scope='Official ideation, MinimalAgent and execution review; bounded four-node trajectory, not full BFTS, VLM or paper reproduction',host='priority server',cpu_threads=4,gpu=False)
(OUT/'STATUS.json').write_text(json.dumps(status,indent=2));print(a.case,a.phase,status['status'],flush=True)
