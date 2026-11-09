from pathlib import Path
import json,sys,time,traceback,importlib,argparse
from types import SimpleNamespace
from openai import OpenAI
ROOT=Path(__file__).resolve().parents[1];UP=ROOT.parent/'replication_selection_20261108/sources/code'
CFG=json.loads((ROOT/'model_config.json').read_text());MODEL=CFG['model']
class Proxy:
 def __init__(self,group,max_tokens):
  self.client=OpenAI(base_url=json.loads((ROOT/'gateway_endpoint.json').read_text())['base_url'],api_key=group,max_retries=0,timeout=240);self.max_tokens=max_tokens
  self.chat=SimpleNamespace(completions=SimpleNamespace(create=self.create))
 def create(self,model,messages,**kwargs):
  for attempt in range(3):
   try:return self.client.chat.completions.create(model=MODEL,messages=messages,max_tokens=self.max_tokens)
   except Exception as exc:
    if attempt == 2 or not any(t in str(exc) for t in ['Connection error', 'timed out', 'timeout']):raise
    time.sleep(2*(attempt+1))
 def call(self,messages,**kwargs):
  return self.create(MODEL,messages).choices[0].message.content

def researchagent(case,out,phase='generation'):
 sys.path.insert(0,str(UP/'researchagent/code'))
 from pipelines.research_pipeline import ResearchPipeline
 dossier=json.loads((ROOT/'cases'/case/'dossier.json').read_text())
 extra=(json.loads((ROOT/'cases'/case/'correction_packet.json').read_text()) if phase=='correction' else None)
 ctx={'paper':{'title':'Historical measurement case','abstract':json.dumps(dossier,ensure_ascii=False)},'references':[],'entities':list(dossier['data_dictionary'])}
 if extra:
  from pipelines.agents.problem_identifier import ProblemIdentifier
  from pipelines.agents.problem_validator import ProblemValidator
  client=Proxy(f'{case}/researchagent/correction',1500)
  agent=ProblemIdentifier(client);reviewer=ProblemValidator(client)
  ctx['paper']['abstract']+='\nAudit task: '+json.dumps(extra)+'\nProvide item-by-item judgments and corrected values before proposing a follow-up question. Use Problem/Rationale format.'
  history=[]
  for _ in range(2):
   ctx.update(agent.run(ctx));ctx.update(reviewer.run(ctx));history.append({k:v for k,v in ctx.items() if k.startswith('problem')})
  result={'history':history,'final':ctx}
 else:result=ResearchPipeline(api_client=Proxy(f'{case}/researchagent/generation',850),iterations=3).run(ctx)
 (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
 return result

def virtual_lab(case,out,phase='generation'):
 sys.path.insert(0,str(UP/'virtual_lab/src'))
 rm=importlib.import_module('virtual_lab.run_meeting');from virtual_lab.agent import Agent
 rm.OpenAI=lambda:Proxy(f'{case}/virtual_lab/{phase}',1400 if phase=='generation' else 1500)
 rm.print_cost_and_time=lambda **kwargs:None
 # Every upstream role, including the built-in critic, is routed to the same requested model.
 rm.SCIENTIFIC_CRITIC.model=MODEL
 dossier=(ROOT/'cases'/case/'dossier.json').read_text()
 domain='optical polarization and photonic computing' if case=='optical' else 'active mechanical metamaterials and nonequilibrium dynamics'
 lead=Agent('Principal Investigator',domain,'develop substantive hypotheses grounded in supplied source data','integrate competing explanations and preserve unresolved questions',MODEL)
 members=(Agent('Domain Scientist',domain,'understand the measured system','develop specific scientific explanations and consequences',MODEL),Agent('Dynamical and Statistical Physicist','stochastic processes, inverse problems and nonlinear dynamics','connect disciplinary concepts to measured relations','challenge assumptions and derive alternative consequences',MODEL))
 common=dict(save_dir=out,contexts=(dossier,),pubmed_search=False,return_summary=True)
 if phase=='correction':
  audit=(ROOT/'cases'/case/'correction_packet.json').read_text()
  result=rm.run_meeting(meeting_type='individual',save_name='audit',team_member=members[0],agenda='Audit each numbered statement, correct actual errors with numbers and distinguish unsupported from false. '+audit,num_rounds=2,**common)
 else:
  agenda='Develop follow-up research hypotheses and concrete conditional consequences beyond the supplied study. Discuss observations and competing explanations; do not claim the paper conclusions as new.'
  initial=rm.run_meeting(meeting_type='team',save_name='01_team',team_lead=lead,team_members=members,num_rounds=3,agenda=agenda,**common)
  refined=[]
  for i,member in enumerate(members):
   refined.append(rm.run_meeting(meeting_type='individual',save_name=f'02_individual_{i}',team_member=member,num_rounds=2,agenda='Develop or challenge the central explanatory assumption from the team discussion; state a substantive conditional consequence and what remains unresolved.',summaries=(initial,),**common))
  result=rm.run_meeting(meeting_type='team',save_name='03_synthesis',team_lead=lead,team_members=members,num_rounds=2,agenda='Compare the developed alternatives and record final specific research questions and hypotheses, their consequences and evidence limits.',summaries=tuple(refined),**common)
 (out/'result.json').write_text(json.dumps({'final':result},ensure_ascii=False,indent=2));return result

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--case',required=True);ap.add_argument('--system',choices=['researchagent','virtual_lab'],required=True);ap.add_argument('--phase',default='generation',choices=['generation','correction']);args=ap.parse_args()
 out=ROOT/'runs'/args.case/args.system/args.phase;out.mkdir(parents=True,exist_ok=True);start=time.monotonic()
 try:
  globals()[args.system](args.case,out,args.phase);status={'status':'complete'}
 except Exception as e:status={'status':'budget_exhausted' if 'BUDGET_EXHAUSTED' in str(e) else 'failed','error':str(e),'traceback':traceback.format_exc()}
 status.update(requested_model=MODEL,seconds=time.monotonic()-start,scope='Official discussion algorithms with common-data adapter and bounded resources; not original paper metric replication')
 (out/'STATUS.json').write_text(json.dumps(status,indent=2));print(args.case,args.system,args.phase,status['status'],flush=True)
