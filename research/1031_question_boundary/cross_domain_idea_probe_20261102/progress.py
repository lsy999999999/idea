"""Read completed state only; export every idea branch without originality filtering."""
import argparse
import json
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parent
LABELS={'materials':'材料','health':'健康监测','education':'教育','transport':'交通','environment':'环境','energy':'能源'}

def state(run):
    for path in sorted((run/'states').glob('*.json'),reverse=True):
        try:return json.loads(path.read_text())
        except (ValueError,OSError):continue
    return {'replies':[],'tools':[],'final':None,'counters':{'replies':0}}

def format_value(value):
    if isinstance(value,str):return value
    return json.dumps(value,ensure_ascii=False,indent=2)

def export_ideas(rows):
    out=['# 全部idea与修改分支','',
         '自动导出已完成并入账的回复。保留初始候选、执行者批评／修改及最终保留或撤回；未按原创性筛除。原始证据仍在各轮sealed_replies及状态版本中。','']
    for run,s in rows:
        out += ['## '+run.name,'']
        for record in s['replies']:
            reply=record['reply'];label=record['label']
            out += ['### '+label,'',format_value(reply.get('summary','')),'']
            for candidate in reply.get('candidates',[]):
                out += ['#### '+str(candidate.get('id',''))+' '+str(candidate.get('title','')),'']
                for key,value in candidate.items():
                    if key in {'id','title'}:continue
                    out += ['**'+key+'**','',format_value(value),'']
            if reply.get('critique'):out += ['**执行者批评／修改**','',format_value(reply['critique']),'']
            if reply.get('final'):out += ['**最终记录（含保留、修改或撤回）**','',format_value(reply['final']),'']
        if not s['replies']:out += ['尚无已完成回复。','']
    target=ROOT/'IDEA_LINES.md';temporary=ROOT/f'.idea_lines_{os.getpid()}.tmp'
    temporary.write_text('\n'.join(out));temporary.replace(target)
    return target

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--json',action='store_true');args=parser.parse_args()
    rows=[(run,state(run)) for run in sorted((ROOT/'runs').iterdir()) if run.is_dir()]
    summary=[];ideas=0
    for run,s in rows:
        count=s['counters']['replies'];ideas+=sum(len(r['reply'].get('candidates',[])) for r in s['replies'] if r['label']=='L1')
        complete=(run/'FROZEN.json').exists()
        blocked=(run/'TRANSPORT_FAILURE.json').exists()
        searches=any(t['result']['status']=='waiting_external' for t in s['tools'])
        status='完成' if complete else ('需查看错误' if blocked else ('检索中' if searches else '排队／运行中'))
        summary.append(dict(run=run.name,domain=LABELS[run.name.rsplit('_',1)[0]],replicate=int(run.name.rsplit('_',1)[1]),completed_replies=count,status=status))
    target=export_ideas(rows)
    totals=dict(completed_runs=sum(r['status']=='完成' for r in summary),planned_runs=12,completed_role_replies=sum(r['completed_replies'] for r in summary),planned_role_replies=36,initial_ideas_retained=ideas,idea_file=str(target),runs=summary)
    if args.json:print(json.dumps(totals,ensure_ascii=False,indent=2));return
    print(f"已完成 {totals['completed_runs']}/12 轮；角色回复 {totals['completed_role_replies']}/36；已保留初始idea {ideas} 条。")
    print('领域       重复  回复  状态')
    for row in summary:print(f"{row['domain']:<10} {row['replicate']}     {row['completed_replies']}/3   {row['status']}")
    print('\n全部idea及分支：'+str(target))
    print('原始记录：'+str(ROOT/'runs'))

if __name__=='__main__':main()
