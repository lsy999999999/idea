"""Postrun provenance, numerical replay and complete candidate export."""
import concurrent.futures as cf
import json
import math
import os
from pathlib import Path
import subprocess
import sys
sys.dont_write_bytecode=True
import pilot as p
ROOT=p.ROOT

def same(a,b):
    if isinstance(a,bool) or isinstance(b,bool):return a is b
    if isinstance(a,(float,int)) and isinstance(b,(float,int)):
        return math.isclose(a,b,rel_tol=1e-9,abs_tol=1e-9) or (math.isnan(a) and math.isnan(b))
    if isinstance(a,dict) and isinstance(b,dict):return a.keys()==b.keys() and all(same(a[k],b[k]) for k in a)
    if isinstance(a,list) and isinstance(b,list):return len(a)==len(b) and all(same(x,y) for x,y in zip(a,b))
    return a==b

def replay():
    scripts=list((ROOT/'runs').glob('*/r*/tools/compute_*/executed.py'))
    def one(script):
        original=p.read(script.parent/'execution.json')
        if original['status']!='executed':return {'script':str(script.relative_to(ROOT)),'original_status':original['status'],'replayed':False}
        out=ROOT/'audit_replay'/script.relative_to(ROOT/'runs').parent
        out.mkdir(parents=True,exist_ok=True)
        try:
            proc=subprocess.run([p.PYTHON,str(script)],cwd=out,capture_output=True,text=True,timeout=35,env={'PATH':'/opt/homebrew/bin:/usr/bin:/bin','OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','PYTHONDONTWRITEBYTECODE':'1'})
            p.write(out/'stdout.txt',proc.stdout);p.write(out/'stderr.txt',proc.stderr)
            exact=proc.stdout==original['stdout'];numeric=None
            try:numeric=same(json.loads(proc.stdout),json.loads(original['stdout']))
            except (ValueError,TypeError):pass
            return {'script':str(script.relative_to(ROOT)),'replayed':True,'returncode':proc.returncode,'exact':exact,'numeric_equal':numeric,'script_sha256':p.sha(script),'scope':'Reproducibility only, not semantic correctness'}
        except subprocess.TimeoutExpired:
            return {'script':str(script.relative_to(ROOT)),'replayed':True,'timeout':True}
    with cf.ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(one,scripts))
    p.write(ROOT/'NUMERICAL_REPLAY.json',{'time':p.now(),'results':results})
    print(json.dumps(results,indent=2))

def export():
    rows=[];lines=['# 全部候选与修改记录','', '每条原始回复和工具返回保留在对应 runs 目录。这里按原顺序导出，不按质量或新颖性筛选。','']
    for case in p.CASES:
        for arm in p.POLICIES:
            for rnd in range(1,4):
                run=ROOT/'runs'/f'{case}_{arm}'/f'r{rnd}'
                rec=p.read(run/'round_record.json');l1=rec['replies'][0]['reply'];r1=rec['replies'][1]['reply'];l2=rec['replies'][2]['reply']
                lines += [f'## {case} / {arm} / 第{rnd}轮','',f"L1选择 {l1['selected_id']}；实际选择 {rec['effective_selected_id']}。",'']
                for c in l1['candidates']:
                    lines += [f"### {c['id']}：{c['title']}",'','```json',json.dumps(c,ensure_ascii=False,indent=2),'```','']
                lines += ['### 批评与实际工具返回','','```json',json.dumps({'critique':r1.get('critique'),'tools':rec['tools']},ensure_ascii=False,indent=2),'```','','### 最终记录','','```json',json.dumps(l2,ensure_ascii=False,indent=2),'```','']
                rows.append({'case':case,'arm':arm,'round':rnd,'proposed':l1['selected_id'],'effective':rec['effective_selected_id'],'titles':[c['title'] for c in l1['candidates']],'final':l2['final'],'tools':[{'type':t['type'],'id':t['id'],'status':t['result']['status']} for t in rec['tools']]})
    p.write(ROOT/'CANDIDATES.md','\n'.join(lines))
    p.write(ROOT/'ROUND_SUMMARY.json',rows)
    print(json.dumps([{k:v for k,v in r.items() if k!='final'} for r in rows],ensure_ascii=False,indent=2))

def integrity():
    p.verify_freeze();checked=0
    for freeze in (ROOT/'runs').glob('*/r*/COMPLETE.json'):
        for name,h in p.read(freeze)['files'].items():
            assert p.sha(freeze.parent/name)==h,str(freeze.parent/name);checked+=1
    for name,h in p.read(ROOT/'REVIEW_PREFREEZE.json')['files'].items():assert p.sha(ROOT/name)==h,name
    base=ROOT.parent if ROOT.name=='format_recovery' else ROOT
    old=base.parent/'cross_domain_idea_probe_20261102'
    old_results=[]
    for freeze in (old/'runs').glob('*/FROZEN.json'):
        mismatches=[name for name,h in p.read(freeze)['files'].items() if not (freeze.parent/name).exists() or p.sha(freeze.parent/name)!=h]
        old_results.append({'run':freeze.parent.name,'mismatches':mismatches})
    p.write(ROOT/'INTEGRITY_AUDIT.json',{'time':p.now(),'new_files_verified':checked,'new_freeze_passed':True,'prior_runs':old_results,'prior_runs_passed':all(not r['mismatches'] for r in old_results)})
    print(json.dumps({'new_files_verified':checked,'prior_runs':len(old_results),'prior_runs_passed':all(not r['mismatches'] for r in old_results)}))

if __name__=='__main__':{'replay':replay,'export':export,'integrity':integrity}[sys.argv[1]]()
