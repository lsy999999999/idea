"""Run the official publication-period application, with an isolated memory."""
from pathlib import Path
import os
import sys
import json
import time
import tomllib
import traceback

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'runs/evoscientist';OUT.mkdir(parents=True,exist_ok=True)
WORK=OUT/'workspace';WORK.mkdir(exist_ok=True)
for key,folder in [('WORKSPACE','workspace'),('MEMORY','memory'),('SKILLS','skills'),('RUNS','sessions')]:
    p=OUT/folder;p.mkdir(exist_ok=True);os.environ['EVOSCIENTIST_'+key+'_DIR']=str(p)
sys.path.insert(0,str(next((ROOT/'upstream').glob('EvoScientist-*'))))

def main():
    from langchain_openai import ChatOpenAI
    from langchain_core.callbacks import BaseCallbackHandler
    from langchain_core.messages import HumanMessage
    from EvoScientist.config import EvoScientistConfig
    import importlib
    evo=importlib.import_module('EvoScientist.EvoScientist')
    class Trace(BaseCallbackHandler):
        def on_chat_model_start(self,serialized,messages,**kwargs):
            p=OUT/'calls';p.mkdir(exist_ok=True)
            (p/(str(kwargs['run_id'])+'.request.json')).write_text(json.dumps([[m.model_dump() for m in row] for row in messages],ensure_ascii=False,indent=2,default=str))
        def on_llm_end(self,response,**kwargs):
            p=OUT/'calls';p.mkdir(exist_ok=True)
            (p/(str(kwargs['run_id'])+'.response.json')).write_text(json.dumps(response.model_dump(),ensure_ascii=False,indent=2,default=str))
        def on_llm_error(self,error,**kwargs):
            (OUT/'model_error.txt').write_text(type(error).__name__+': '+str(error))
    cfg=tomllib.loads(Path('/Users/LSY/.codex/config.toml').read_text())
    auth=json.loads(Path('/Users/LSY/.codex/auth.json').read_text())
    evo._chat_model=ChatOpenAI(model='gpt-6-luna',api_key=auth['OPENAI_API_KEY'],
         base_url=cfg['model_providers'][cfg['model_provider']]['base_url'],
         use_responses_api=True,reasoning={'effort':'low'},max_tokens=2500,
         timeout=120,max_retries=1,callbacks=[Trace()])
    config=EvoScientistConfig(provider='openai',model='gpt-6-luna',auto_approve=True,enable_ask_user=False)
    (WORK/'case_context.json').write_text((ROOT/'case_context.json').read_text())
    prompt='Read /case_context.json and develop one substantive early-stage research idea about impedance-based battery SOH estimation. Use only the supplied sources; online search is unavailable in this small pilot. You may use at most one research-agent subtask and at most 8 tool calls. Save the final idea with its hypothesis, scientific consequences, and source limits to /idea.md. Save a concise reusable research lesson to /memory/ideation-memory.md. Do not implement experiments in this ideation-only task. Then return the idea in your final response.'
    results=[]
    for index,question in enumerate([prompt,'Start from the saved /memory/ideation-memory.md and /idea.md. Identify one assumption that could be revised to form a different research direction, explain the scientific consequence, and save it to /continuation.md. Use only the supplied materials, at most 4 tool calls, and no online search.']):
        agent=evo.create_cli_agent(workspace_dir=str(WORK),config=config)
        state=agent.invoke({'messages':[HumanMessage(content=question)]},config={'configurable':{'thread_id':'evo_pilot_'+str(index)},'recursion_limit':64})
        data={'messages':[m.model_dump() for m in state['messages']]}
        (OUT/f'session_{index}.json').write_text(json.dumps(data,ensure_ascii=False,indent=2,default=str))
        results.append({'session':index,'final':state['messages'][-1].content})
        print('EvoScientist session',index,'complete',flush=True)
    return {'status':'complete','model':'gpt-6-luna','sessions':results,'scope':'Official publication-period application on one supplied literature case, plus a fresh graph continuation. This is not reproduction of the paper three-role memory benchmark.'}

if __name__=='__main__':
    start=time.time()
    try:result=main()
    except Exception as e:result={'status':'failed','error':type(e).__name__+': '+str(e),'traceback':traceback.format_exc()}
    result['seconds']=time.time()-start
    (OUT/'STATUS.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print('EvoScientist',result['status'],result.get('error',''),flush=True)
