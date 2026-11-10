"""Official AI-Scientist-v2 ideation and two CPU implementation/review nodes."""
from pathlib import Path
import os,sys,json,time,uuid,ast,traceback
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'runs/scientist_v2';OUT.mkdir(parents=True,exist_ok=True)
QUEUE=ROOT/'requests';QUEUE.mkdir(exist_ok=True)
MODEL='deepseek-flash'
UP=next(Path('/home/lsy/ideas_replication_20261108/upstream').glob('AI-Scientist-v2-*'));sys.path.insert(0,str(UP))

def request(messages,function=None,tool=None):
 uid=uuid.uuid4().hex;p=QUEUE/(uid+'.request.json')
 payload={'messages':messages,'function':function,'tool':tool};tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(payload));tmp.replace(p)
 a=QUEUE/(uid+'.answer.json');start=time.monotonic()
 while not a.exists():
  if time.monotonic()-start>1800:raise TimeoutError('Local model bridge timeout')
  time.sleep(.3)
 result=json.loads(a.read_text())
 if 'error' in result:raise RuntimeError(result['error'])
 return result['result']

def response_from_llm(prompt,client,model,system_message,msg_history=None,**kw):
 history=(msg_history or [])+[{'role':'user','content':prompt}]
 text=request([{'role':'system','content':system_message}]+history)
 return text,history+[{'role':'assistant','content':text}]

def tree_query(system_message=None,user_message=None,func_spec=None,**kw):
 from ai_scientist.treesearch.backend import compile_prompt_to_md
 messages=[]
 if system_message:messages.append({'role':'system','content':compile_prompt_to_md(system_message)})
 if user_message:messages.append({'role':'user','content':compile_prompt_to_md(user_message)})
 function={'name':func_spec.name,'description':func_spec.description,'parameters':func_spec.json_schema} if func_spec else None
 return request(messages,function)

def validate(code):
 """Constrain generated computations to installed numeric libraries and the supplied CSV."""
 tree=ast.parse(code)
 imports={'numpy','pandas','scipy','math','statistics','itertools','collections','json','matplotlib','typing','warnings'}
 forbidden={'open','exec','eval','compile','getattr','setattr','globals','locals','vars','input','__import__','breakpoint','help','dir'}
 badattr={'load','loads','loadtxt','genfromtxt','fromfile','memmap','save','savez','savetxt','read_pickle','read_json','read_html','read_excel','read_sql','to_pickle','to_csv','to_json','to_excel','to_sql','query','eval','ctypes','system','popen','dump','dumps','show','use','get_backend','imread','imsave','chdir','get_data','read_table','read_fwf','read_parquet','read_feather','read_orc','read_xml','read_hdf','read_sas','read_spss','read_stata','read_clipboard','read_gbq','read_sql_query','read_sql_table'}
 for n in ast.walk(tree):
  if isinstance(n,(ast.Import,ast.ImportFrom)):
   names=[a.name for a in n.names] if isinstance(n,ast.Import) else [n.module or '']
   for name in names:
    if name.split('.')[0] not in imports or any(t in name.split('.') for t in ['io','lib','ctypeslib','f2py','testing','utils','_lib']):raise ValueError('Unscreened import: '+name)
  if isinstance(n,ast.Name) and (n.id in forbidden or n.id.startswith('__')):raise ValueError('Unsupported runtime capability: '+n.id)
  if isinstance(n,ast.Attribute) and (n.attr.startswith('_') or (n.attr in badattr and n.attr!='use')):raise ValueError('Unsupported capability: '+n.attr)
  if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute):
   if n.func.attr=='use' and not (isinstance(n.func.value,ast.Name) and n.func.value.id=='matplotlib' and len(n.args)==1 and isinstance(n.args[0],ast.Constant) and n.args[0].value=='Agg'):raise ValueError('Only matplotlib.use("Agg") is allowed')
   if n.func.attr.startswith('read_'):
    if n.func.attr!='read_csv' or not n.args or not isinstance(n.args[0],ast.Constant) or n.args[0].value!='measurements.csv':raise ValueError('Only literal measurements.csv may be read')
   if n.func.attr=='savefig':
    if not n.args or not isinstance(n.args[0],ast.Constant) or Path(str(n.args[0].value)).name!=n.args[0].value:raise ValueError('Figure output must be a literal basename')
 return tree

def main():
 os.environ.update(CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='4',MPLBACKEND='Agg')
 from ai_scientist import perform_ideation_temp_free as idea
 from ai_scientist.treesearch import parallel_agent as pa
 from ai_scientist.treesearch.interpreter import Interpreter
 from omegaconf import OmegaConf
 idea.get_response_from_llm=response_from_llm
 idea.semantic_scholar_tool.use_tool=lambda query:json.dumps(request([],tool={'name':'search_sources','arguments':{'queries':[query]}}))
 pa.query=tree_query
 brief=(ROOT/'dossier.json').read_text();work=OUT/'workspace';work.mkdir(exist_ok=True)
 import shutil
 shutil.copy2(ROOT/'measurements.csv',work/'measurements.csv')
 limits='Use actual measurements.csv, 123 supplied rows, pandas/numpy/scipy/matplotlib CPU only, four threads, at most 120 seconds. No downloads or synthetic replacement measurements. Generated code may import numeric libraries only. No os/pathlib/sys/io, no open/eval/exec, no underscore attributes. Read only pd.read_csv("measurements.csv"). Print findings; optional plt.savefig("figure.png"). No other file I/O. All computations must distinguish exploratory fit from mechanism evidence. '
 workshop=brief+'\nDevelop one explanatory scientific hypothesis with an actual mechanism/equations and conditional prediction. Finalize within three reflections; novelty can remain unresolved.'
 p=OUT/'ideas.json'
 ideas=json.loads(p.read_text()) if p.exists() else idea.generate_temp_free_idea(str(p),None,MODEL,workshop,max_num_generations=1,num_reflections=3,reload_ideas=False)
 if not ideas:
  # Preserve the native failure and ask the native model for its completed hypothesis.
  p.with_name('native_ideation_unfinalized.json').write_text(json.dumps({'status':'no_FinalizeIdea_after_three_reflections'}))
  ideas=[{'adapter_completion':request([{'role':'system','content':'Complete one concrete explanatory hypothesis now, with mechanism and conditional prediction.'},{'role':'user','content':workshop}])}]
 task=limits+'\n'+brief+'\nIdea: '+json.dumps(ideas[0])+'\nActually analyze the numeric table to develop or challenge this hypothesis. Print a concrete finding and its limitations.'
 cfg=OmegaConf.load(UP/'bfts_config.yaml');cfg.agent.code.model=MODEL;cfg.agent.feedback.model=MODEL;cfg.agent.num_workers=1
 pa.MinimalAgent._prompt_impl_guideline=property(lambda self:{'Execution requirements':limits,'Output requirements':'Complete executable Python, actual numeric findings; preserve hypothesis assumptions.'})
 pa.MinimalAgent._prompt_environment=property(lambda self:{'Available packages':'numpy pandas scipy sklearn matplotlib; CPU only'})
 agent=pa.MinimalAgent(task_desc=task,cfg=cfg,evaluation_metrics='actual data relations and implications for the hypothesis',stage_name='1_initial_implementation')
 interpreter=Interpreter(work,timeout=120,env_vars={'CUDA_VISIBLE_DEVICES':'','OMP_NUM_THREADS':'4'})
 nodes=[];parent=None
 try:
  for i in range(2):
   if parent is None:node=agent._draft();op='draft'
   elif parent.is_buggy:node=agent._debug(parent);op='debug'
   else:agent.memory_summary=json.dumps(nodes);node=agent._improve(parent);op='improve'
   (OUT/f'node_{i}.py').write_text(node.code)
   try:
    validate(node.code)
    execution=interpreter.run('import os\nos.chdir('+repr(str(work))+')\n'+node.code)
    agent.parse_exec_result(node,execution,str(work))
    rec={'index':i,'operation':op,'plan':node.plan,'analysis':node.analysis,'is_buggy':node.is_buggy,'term_out':execution.term_out,'exc_type':execution.exc_type,'exec_time':execution.exec_time}
   except ValueError as ex:
    node.is_buggy=True;node.analysis='Execution gate: '+str(ex)
    rec={'index':i,'operation':op,'plan':node.plan,'is_buggy':True,'analysis':node.analysis,'execution_status':'blocked_before_execution'}
   nodes.append(rec);(OUT/'nodes.json').write_text(json.dumps(nodes,indent=2,default=str));parent=node
 finally:interpreter.cleanup_session()
 final=request([{'role':'system','content':'Deliver the completed scientific hypothesis report from the actual idea and execution trajectory. Include concrete mechanism/equations, actual measured support, one distinct conditional prediction and competing explanation. Distinguish blocked/failed computations. No invention of execution.'},{'role':'user','content':task+'\nActual nodes:'+json.dumps(nodes,default=str)}])
 (OUT/'native_result.json').write_text(json.dumps({'ideas':ideas,'nodes':nodes,'final':final},indent=2,ensure_ascii=False,default=str))

if __name__=='__main__':
 try:main();s={'status':'native_complete','host':'priority_server','nodes':2,'cpu_threads':4,'gpu':False}
 except Exception as e:s={'status':'failed','error':str(e),'traceback':traceback.format_exc()}
 (OUT/'STATUS.json').write_text(json.dumps(s,indent=2));print(json.dumps(s),flush=True)
