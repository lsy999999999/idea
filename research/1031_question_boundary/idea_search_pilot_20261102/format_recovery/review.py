"""Mask arm labels for a separate-context model review; preserve mappings."""
import concurrent.futures as cf
import copy
import json
from pathlib import Path
import random
import sys
sys.dont_write_bytecode=True
import pilot as p
ROOT=p.ROOT

def strip_candidate(c):
    if c is None:return None
    c=copy.deepcopy(c)
    for k in ['id','history_match','history_relation','quality_gate','discriminating_delta']:
        c.pop(k,None)
    return c

def prepare():
    p.verify_freeze()
    for case in p.CASES:
        records=[];mapping={}
        for arm in p.POLICIES:
            for rnd in range(1,4):
                run=ROOT/'runs'/f'{case}_{arm}'/f'r{rnd}'
                assert (run/'COMPLETE.json').exists(), f'Incomplete {run}'
                rec=p.read(run/'round_record.json')
                l1=rec['replies'][0]['reply'];l2=rec['replies'][2]['reply']['final']
                for c in l1['candidates']:
                    records.append(({'stage':'initial','candidate':strip_candidate(c)}, {'case':case,'arm':arm,'round':rnd,'stage':'initial','candidate_id':c['id']}))
                final=copy.deepcopy(l2);final.pop('candidate',None)
                # Remove subjective novelty declarations while retaining empirical claims.
                final.pop('novelty_status',None)
                records.append(({'stage':'final','candidate':strip_candidate(l2.get('candidate')),'final_record':final,'actual_tools':rec['tools']}, {'case':case,'arm':arm,'round':rnd,'stage':'final','candidate_id':l2.get('candidate',{}).get('id') if l2.get('candidate') else None}))
        random.Random(20261102 + p.CASES[case]).shuffle(records)
        public=[]
        for i,(record,source) in enumerate(records,1):
            opaque=f'K{i:03d}';record['id']=opaque;public.append(record);mapping[opaque]=source
        bundle={'instruction':(ROOT/'REVIEW_INSTRUCTIONS.md').read_text(),'materials':p.read(ROOT/'cases'/f'{case}.json'),'records':public}
        p.write(ROOT/'review_inputs'/f'{case}.json',bundle)
        p.write(ROOT/'review_mapping'/f'{case}.json',mapping)
    p.write(ROOT/'review_inputs/FROZEN.json',{'time':p.now(),'instruction_sha256':p.sha(ROOT/'REVIEW_INSTRUCTIONS.md'),'code_sha256':p.sha(ROOT/'review.py'),'inputs':{case:p.sha(ROOT/'review_inputs'/f'{case}.json') for case in p.CASES}})

def run():
    def one(case):
        reply=p.infer(ROOT/'review_model'/case,p.read(ROOT/'review_inputs'/f'{case}.json'))
        expected=set(p.read(ROOT/'review_mapping'/f'{case}.json'))
        records=reply['records'];actual=[r['id'] for r in records]
        assert len(actual)==len(expected) and set(actual)==expected
        families={r['family_id'] for r in reply['families']}
        assert all(r['family_id'] in families for r in records)
        p.write(ROOT/'review_model'/case/'VALIDATED.json',{'complete_ids':True,'records':len(records),'families':len(families)})
        return case
    with cf.ThreadPoolExecutor(max_workers=2) as pool:
        for case in pool.map(one,p.CASES):print(case,flush=True)

def summarize():
    rows=[]
    for case in p.CASES:
        mapping=p.read(ROOT/'review_mapping'/f'{case}.json')
        judged=p.read(ROOT/'review_model'/case/'reply.json')
        for arm in p.POLICIES:
            initial=[];final=[]
            for j in judged['records']:
                m=mapping[j['id']]
                if m['arm']==arm:
                    (initial if m['stage']=='initial' else final).append({**m,**j})
            final.sort(key=lambda x:x['round'])
            allfam=set();curve=[]
            for item in final:
                if item['usable_final']:allfam.add(item['family_id'])
                curve.append(len(allfam))
            usages=[]
            for f in (ROOT/'runs'/f'{case}_{arm}').glob('r*/*/completion_attempt*.json'):usages.append(p.read(f))
            costs={k:sum(u['usage'].get(k,0) for u in usages) for k in ['input_tokens','output_tokens','reasoning_output_tokens','cached_input_tokens']}
            rows.append({'case':case,'arm':arm,'initial_valid':sum(i['proposal_quality'] for i in initial),'initial_valid_families':len({i['family_id'] for i in initial if i['proposal_quality']}),'final_usable':sum(i['usable_final'] for i in final),'final_unique_families':len(allfam),'cumulative_unique':curve,'material_errors':sum(i['material_acceptance_error'] for i in final),'initial':initial,'final':final,'usage':costs,'call_seconds_sum':sum(u['seconds'] for u in usages)})
    p.write(ROOT/'MODEL_REVIEW_SUMMARY.json',{'time':p.now(),'source':'Same-model masked-context review; requires organizer audit','rows':rows})
    print(json.dumps([{k:v for k,v in r.items() if k not in ['initial','final']} for r in rows],ensure_ascii=False,indent=2))

if __name__=='__main__':{'prepare':prepare,'run':run,'summarize':summarize}[sys.argv[1]]()
