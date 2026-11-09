from pathlib import Path
import sys
import json
import time
import traceback
from concurrent.futures import ThreadPoolExecutor,as_completed
from model_adapter import MODEL,ResearchClient,ChatClient

ROOT=Path(__file__).resolve().parent
UP=ROOT.parent/'sources/code'
context=json.loads((ROOT/'case_context.json').read_text())

def researchagent():
    sys.path.insert(0,str(UP/'researchagent/code'))
    from pipelines.research_pipeline import ResearchPipeline
    out=ROOT/'runs/researchagent';out.mkdir(parents=True,exist_ok=True)
    result=ResearchPipeline(api_client=ResearchClient(),iterations=2).run(context.copy())
    (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    return {'problem':result.get('problem'),'method':result.get('method'),'experiment':result.get('experiment')}

def virtual_lab():
    sys.path.insert(0,str(UP/'virtual_lab/src'))
    import importlib
    rm=importlib.import_module('virtual_lab.run_meeting')
    from virtual_lab.agent import Agent
    rm.OpenAI=ChatClient
    rm.print_cost_and_time=lambda **kwargs:print('Virtual Lab: provider billing unknown; actual usage retained in responses',flush=True)
    out=ROOT/'runs/virtual_lab';out.mkdir(parents=True,exist_ok=True)
    lead=Agent('Principal Investigator','battery research and interdisciplinary scientific reasoning','identify a useful research question','lead a concrete discussion and synthesize the conclusions',MODEL)
    members=(Agent('Electrochemist','electrochemical impedance and battery degradation','understand the material and propose research directions','contribute domain reasoning and respond to colleagues',MODEL),Agent('Dynamical Systems Researcher','inverse problems and dynamical systems','identify transferable concepts and useful hypotheses','question assumptions and develop scientific consequences',MODEL))
    summary=rm.run_meeting(meeting_type='team',agenda='Develop one scientifically substantive research direction about impedance-based battery state-of-health estimation from the supplied literature. Explain the hypothesis and consequences. This is an early idea discussion.',save_dir=out,save_name='meeting',team_lead=lead,team_members=members,num_rounds=1,contexts=(json.dumps(context,ensure_ascii=False),),pubmed_search=False,return_summary=True)
    return {'summary':summary}

def run(name,fn):
    start=time.time();out=ROOT/'runs'/name;out.mkdir(parents=True,exist_ok=True)
    try:result={'status':'complete','result':fn()}
    except Exception as e:result={'status':'failed','error':str(e),'traceback':traceback.format_exc()}
    result.update(model=MODEL,seconds=time.time()-start,scope='single-case adapted official workflow; not paper metric replication')
    (out/'STATUS.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(name,result['status'],flush=True)

if __name__=='__main__':
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(run,'researchagent',researchagent),pool.submit(run,'virtual_lab',virtual_lab)]
        for f in as_completed(futures):f.result()
