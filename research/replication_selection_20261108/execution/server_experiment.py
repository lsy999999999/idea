"""One official AI Scientist-v2 ideation plus initial implementation node."""
from pathlib import Path
import json
import os
import sys
import time
import traceback
import uuid

ROOT=Path(__file__).resolve().parent
UP=next((ROOT/'upstream').glob('AI-Scientist-v2-*'))
sys.path.insert(0,str(UP))
OUT=ROOT/'results';OUT.mkdir(exist_ok=True)
QUEUE=ROOT/'requests';QUEUE.mkdir(exist_ok=True)

def request(payload):
    uid=uuid.uuid4().hex
    p=QUEUE/(uid+'.request.json');p.write_text(json.dumps(payload,ensure_ascii=False))
    answer=QUEUE/(uid+'.answer.json')
    start=time.time()
    while not answer.exists():
        if time.time()-start>240:raise TimeoutError('Local model bridge timed out')
        time.sleep(.25)
    data=json.loads(answer.read_text())
    if 'error' in data:raise RuntimeError(data['error'])
    return data['result']

def response_from_llm(prompt,client,model,system_message,msg_history=None,**kwargs):
    history=(msg_history or [])+[{'role':'user','content':prompt}]
    text=request({'kind':'model','messages':[{'role':'system','content':system_message}]+history,'max_tokens':3800})
    return text,history+[{'role':'assistant','content':text}]

def tree_query(system_message=None,user_message=None,func_spec=None,**kwargs):
    from ai_scientist.treesearch.backend import compile_prompt_to_md
    messages=[]
    if system_message:messages.append({'role':'system','content':compile_prompt_to_md(system_message)})
    if user_message:messages.append({'role':'user','content':compile_prompt_to_md(user_message)})
    function=({'name':func_spec.name,'description':func_spec.description,'json_schema':func_spec.json_schema} if func_spec else None)
    return request({'kind':'model','messages':messages,'function':function,'max_tokens':6500 if not function else 1800})

def main():
    os.environ['CUDA_VISIBLE_DEVICES']='0'
    os.environ['MPLBACKEND']='Agg'
    import torch
    torch.set_num_threads(4)
    from ai_scientist import perform_ideation_temp_free as ideation
    from ai_scientist.treesearch import parallel_agent as pa
    from ai_scientist.treesearch.interpreter import Interpreter
    from omegaconf import OmegaConf
    ideation.get_response_from_llm=response_from_llm
    ideation.semantic_scholar_tool.use_tool=lambda query:request({'kind':'literature','query':query})
    pa.query=tree_query
    workshop=(UP/'ai_scientist/ideas/i_cant_believe_its_not_better.md').read_text()
    workshop+='\n\nSmall reproduction budget: propose a simple controlled deep-learning experiment about distribution shift or shortcut reliance, using one synthetic dataset generated with NumPy/PyTorch. Use at most 2048 training examples, 512 validation examples and 5 epochs per condition, a small MLP, and at most 3 conditions. Use fixed seeds and separate training/validation sets. No external dataset or model downloads. An NVIDIA GPU is available. Guaranteed libraries: torch, numpy, scikit-learn, pandas, matplotlib. This is a small pilot, so state uncertainty about generality.'
    (OUT/'workshop_input.md').write_text(workshop)
    ideas=json.loads((OUT/'ideas.json').read_text()) if (OUT/'ideas.json').exists() else []
    if not ideas:
        ideas=ideation.generate_temp_free_idea(str(OUT/'ideas.json'),None,'gpt-6-luna',workshop,max_num_generations=1,num_reflections=5,reload_ideas=False)
    if not ideas:raise RuntimeError('Original ideation loop did not finalize an idea within five rounds')
    cfg=OmegaConf.load(UP/'bfts_config.yaml');cfg.agent.code.model='gpt-6-luna';cfg.agent.feedback.model='gpt-6-luna';cfg.agent.num_workers=1
    agent=pa.MinimalAgent(task_desc=json.dumps(ideas[0]),cfg=cfg,evaluation_metrics='validation accuracy and validation loss for each condition',stage_name='1_initial_implementation')
    work=OUT/'workspace';work.mkdir(exist_ok=True)
    interpreter=Interpreter(work,timeout=180,env_vars={'CUDA_VISIBLE_DEVICES':'0','OMP_NUM_THREADS':'4'})
    node=agent._draft()
    attempts=[]
    try:
        for attempt in range(2):
            (OUT/f'code_attempt_{attempt}.py').write_text(node.code)
            (OUT/f'plan_attempt_{attempt}.md').write_text(node.plan)
            code='import os\nworking_dir='+repr(str(work))+'\nos.makedirs(working_dir, exist_ok=True)\n'+node.code
            execution=interpreter.run(code)
            record={'attempt':attempt,'term_out':execution.term_out,'exec_time':execution.exec_time,'exc_type':execution.exc_type,'exc_info':execution.exc_info}
            attempts.append(record);(OUT/'executions.json').write_text(json.dumps(attempts,ensure_ascii=False,indent=2))
            agent.parse_exec_result(node,execution,str(work))
            (OUT/f'node_attempt_{attempt}.json').write_text(json.dumps(node.to_dict(),ensure_ascii=False,indent=2,default=str))
            if execution.exc_type is None:break
            if attempt==0:node=agent._debug(node)
    finally:interpreter.cleanup_session()
    return {'status':'complete' if attempts[-1]['exc_type'] is None else 'experiment_failed','model':'gpt-6-luna','gpu':torch.cuda.get_device_name(0),'idea':ideas[0],'attempts':attempts,'scope':'Official ideation + one MinimalAgent draft/optional debug + official execution review. Four-stage search, VLM plots and paper writing not run.'}

if __name__=='__main__':
    start=time.time()
    try:result=main()
    except Exception as exc:result={'status':'failed','error':str(exc),'traceback':traceback.format_exc()}
    result['seconds']=time.time()-start
    (OUT/'STATUS.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print('FINAL',result['status'],flush=True)
