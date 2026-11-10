from common import *
import argparse,os,traceback,importlib,threading,fcntl
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler

def researchagent(e):
 sys.path.insert(0,str(UP/'sources/code/researchagent/code'))
 from pipelines.research_pipeline import ResearchPipeline
 ctx={'paper':{'title':'Anonymous mechanical measurement case','abstract':json.dumps(brief(),ensure_ascii=False)},'references':[],'entities':list(brief()['data_dictionary'])}
 pipeline=ResearchPipeline(api_client=Proxy(e),iterations=1)
 result=pipeline.run(ctx)
 if result.get('method') and result.get('method_feedbacks'):
  result['pre_revision_method']=result['method']
  result.update(pipeline.method_developer.run(result))
  result['extra_step']='One native method refinement after feedback; experiment plan refers to the pre-refinement method.'
 dump(e.out/'native_result.json',result)
 return result

def virtual_lab(e):
 sys.path.insert(0,str(UP/'sources/code/virtual_lab/src'))
 rm=importlib.import_module('virtual_lab.run_meeting');from virtual_lab.agent import Agent
 rm.OpenAI=lambda:Proxy(e);rm.print_cost_and_time=lambda **kw:None
 rm.SCIENTIFIC_CRITIC.model=CFG['model']
 lead=Agent('Principal Investigator','mechanical hysteresis','develop explanatory hypotheses','integrate concrete derivations and conditional predictions',CFG['model'])
 members=(Agent('Mechanics Scientist','rigid-body mechanics, elastic mechanisms and quasistatic experiments','develop case-grounded hypotheses','derive mechanical relations from actual measurements',CFG['model']),Agent('Theory Scientist','nonlinear dynamics, hysteresis and statistical physics','develop alternative mechanisms','derive consequences and challenge premises',CFG['model']))
 common={'save_dir':e.out,'contexts':(json.dumps(brief(),ensure_ascii=False),),'pubmed_search':False,'return_summary':True}
 first=rm.run_meeting(meeting_type='team',save_name='01_team',team_lead=lead,team_members=members,num_rounds=1,agenda='Develop concrete explanatory hypotheses and distinguishable consequences from the supplied data. Reach a working mechanism, not just a measurement plan.',**common)
 revised=rm.run_meeting(meeting_type='individual',save_name='02_individual',team_member=members[1],num_rounds=1,agenda='Actually develop, correct or extend one mechanism from the team meeting. Include equations, scope and a distinguishing prediction.',summaries=(first,),**common)
 final=rm.run_meeting(meeting_type='team',save_name='03_synthesis',team_lead=lead,team_members=members,num_rounds=1,agenda='Select 1-3 actual hypotheses from the discussions. Integrate the developed equations, measured support and conditional predictions. Deliver a completed hypothesis report.',summaries=(first,revised),**common)
 result={'team':first,'individual':revised,'final':final};dump(e.out/'native_result.json',result);return result

def evo(e):
 for key,folder in [('WORKSPACE','workspace'),('MEMORY','memory'),('SKILLS','skills'),('RUNS','sessions')]:
  p=e.out/folder;p.mkdir(exist_ok=True);os.environ['EVOSCIENTIST_'+key+'_DIR']=str(p)
 sys.path.insert(0,str(next((UP/'execution/upstream').glob('EvoScientist-*'))))
 from langchain_openai import ChatOpenAI
 from langchain_core.messages import HumanMessage
 from langchain_core.tools import tool
 from EvoScientist.config import EvoScientistConfig
 ev=importlib.import_module('EvoScientist.EvoScientist')
 from deepagents.backends import FilesystemBackend
 import EvoScientist.backends as backends
 # Native planning/delegation/memory graph, with a filesystem-only backend.
 # All external scientific access is routed through the same screened tools.
 backends.CustomSandboxBackend=lambda root_dir,virtual_mode=True,timeout=300:FilesystemBackend(root_dir=root_dir,virtual_mode=virtual_mode)
 @tool
 def research_tool(name:str,arguments:dict)->str:
  """Call a screened scientific tool. name and arguments follow the provided tool catalog; supports full CSV analysis, dated literature and neutral definitions."""
  return json.dumps(e.science_call(name,arguments,uuid.uuid4().hex),ensure_ascii=False)
 original=ev._build_base_kwargs
 def build(be,mw):
  kw=original(be,mw);kw['tools']=[research_tool]
  for sub in kw['subagents']:
   sub['tools']=[research_tool];sub['model']=ev._chat_model
  kw['system_prompt']+='\n'+RULES+'\nFor this bounded hypothesis task, use at most one delegation; directly write concrete mechanisms and final hypotheses. Shell execution is replaced with analyze_csv through research_tool.'
  return kw
 ev.load_mcp_and_build_kwargs=build
 class Handler(BaseHTTPRequestHandler):
  def log_message(self,*a):pass
  def do_POST(self):
   try:
    p=json.loads(self.rfile.read(int(self.headers['Content-Length'])));msgs=p['messages']
    msgs.insert(0,{'role':'system','content':RULES})
    delivery=any(m.get('role')=='user' and 'FINAL_DELIVERY:' in str(m.get('content','')) for m in msgs) and any(t.get('function',{}).get('name') in {'task','read_file','write_todos','research_tool'} for t in p.get('tools',[]))
    r=e.raw(msgs,None if delivery else p.get('tools'),None if delivery else p.get('tool_choice'))
    data=json.dumps(r.model_dump()).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(data)
   except Exception as ex:
    data=json.dumps({'error':{'message':str(ex),'type':'local_bridge'}}).encode();self.send_response(500);self.end_headers();self.wfile.write(data)
 server=ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
 ev._chat_model=ChatOpenAI(model=CFG['model'],api_key='local-placeholder',base_url=f'http://127.0.0.1:{server.server_port}/v1',max_retries=0,timeout=600,use_responses_api=False)
 cfg=EvoScientistConfig(provider='openai',model=CFG['model'],auto_approve=True,enable_ask_user=False)
 work=e.out/'workspace'
 (work/'dossier.json').write_text(json.dumps(brief(),ensure_ascii=False));(work/'measurements.csv').write_bytes((ROOT/'cases/hysteron/measurements.csv').read_bytes())
 prompt=RULES+'\nCOMMON CASE:\n'+json.dumps(brief(),ensure_ascii=False)+'\nSCREENED TOOL SCHEMAS:\n'+json.dumps(e.tools.definitions,ensure_ascii=False)+'\nComplete one compact research cycle now. Use your native planning/delegation and memory as helpful, at most one delegation. Produce 1-3 specific explanatory hypotheses with actual derivation or data relations and distinguishable predictions, save /final.md and reusable notes in /memory/. Tools are optional; complete the final hypotheses in this session.'
 agent=ev.create_cli_agent(workspace_dir=str(work),config=cfg)
 last=None;interrupted=None;delivery_completed=False
 try:
  prior=e.out/'native_result.json'
  if prior.exists() and json.loads(prior.read_text()).get('native_boundary'):
   from langchain_core.messages import messages_from_dict
   saved=json.loads(prior.read_text());last={'messages':messages_from_dict([{'type':m['type'],'data':m} for m in saved['messages']])};interrupted=saved['native_boundary']
  else:
   try:
    for state in agent.stream({'messages':[HumanMessage(content=prompt)]},config={'configurable':{'thread_id':'hysteron_short'},'recursion_limit':24},stream_mode='values'):
     last=state;dump(e.out/'live_state.json',{'messages':[m.model_dump() for m in state['messages']]})
   except Exception as ex:
    interrupted={'error_type':type(ex).__name__,'error':str(ex)};dump(e.out/'native_boundary.json',interrupted)
  if interrupted and last:
   recovery=last['messages']+[HumanMessage(content='FINAL_DELIVERY: Complete the research task now using the actual discussion and data already obtained. Deliver 1-3 explanatory hypotheses, a mechanism/equation for each, measured support and a distinguishing conditional prediction. Preserve uncertainties. No more tools or plans; your substantive final answer is required now.')]
   for state in agent.stream({'messages':recovery},config={'configurable':{'thread_id':'hysteron_delivery'},'recursion_limit':12},stream_mode='values'):
    last=state;dump(e.out/'delivery_state.json',{'messages':[m.model_dump() for m in state['messages']]})
   delivery_completed=True
 finally:server.shutdown()
 if last is None:raise RuntimeError('No EvoScientist state produced')
 result={'messages':[m.model_dump() for m in last['messages']],'native_boundary':interrupted,'delivery_completed':delivery_completed or not interrupted}
 dump(e.out/'native_result.json',result);return result

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--system',required=True,choices=['researchagent','virtual_lab','evoscientist']);a=ap.parse_args()
 folder=ROOT/'runs'/a.system;folder.mkdir(parents=True,exist_ok=True)
 run_lock=(folder/'.run.lock').open('a');fcntl.flock(run_lock,fcntl.LOCK_EX)
 if (folder/'STATUS.json').exists() and json.loads((folder/'STATUS.json').read_text()).get('status')=='complete':raise SystemExit(0)
 e=Engine(a.system);start=time.monotonic();dump(e.out/'STATUS.json',{'status':'running','system':a.system})
 try:
  target=e.out/'native_result.json'
  saved=json.loads(target.read_text()) if target.exists() else None
  result=saved if saved and not (a.system=='evoscientist' and saved.get('native_boundary') and not saved.get('delivery_completed')) else {'researchagent':researchagent,'virtual_lab':virtual_lab,'evoscientist':evo}[a.system](e)
  final=finalize(e,result);dump(e.out/'STATUS.json',{'status':'generation_complete','system':a.system,'hypotheses':len(final['hypotheses']),'seconds':time.monotonic()-start})
 except Exception as ex:
  dump(e.out/'STATUS.json',{'status':'failed','error_type':type(ex).__name__,'error':str(ex),'traceback':traceback.format_exc()});raise
