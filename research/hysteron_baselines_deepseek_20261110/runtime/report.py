from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[1]
SYSTEMS=['researchagent','virtual_lab','scientist_v2','evoscientist']
def accounting(folder):
 rows=[json.loads(x) for x in (folder/'usage.jsonl').read_text().splitlines()] if (folder/'usage.jsonl').exists() else []
 return {'settled_calls':len(rows),'input_tokens':sum(r['usage'].get('prompt_tokens',0) for r in rows),'output_tokens':sum(r['usage'].get('completion_tokens',0) for r in rows),'reasoning_tokens':sum((r['usage'].get('completion_tokens_details') or {}).get('reasoning_tokens',0) for r in rows),'cache_hit_tokens':sum(r['usage'].get('prompt_cache_hit_tokens',0) for r in rows),'private_definition_calls':sum(bool(r['private_service']) for r in rows)}
def main():
 broad_path=ROOT/'runs/shared_prior_work_evaluation/BROAD_SCOPE_AUDIT.json'
 broad=json.loads(broad_path.read_text()) if broad_path.exists() else {'checks':[]}
 broad_by={(c['system'],c['hypothesis_id']):c for c in broad['checks']}
 audit_path=ROOT/'controller_only/CONTROLLER_AUDIT.json'
 audit=json.loads(audit_path.read_text()) if audit_path.exists() else {'checks':[]}
 audit_by={(c['system'],c['hypothesis_id']):c for c in audit['checks']}
 all_results={};lines=['# 四架构机械迟滞假说短程对照','', '同一 123 行实测输入，DeepSeek 官方 deepseek-flash / high，文献严格早于 2024-09-12。四套使用此前测试的固定版本源码；AI-Scientist-v2 在原优先服务器运行。具体适配与回合见 PROTOCOL_CN.md。','', '## 交付与实际用量','', '| 架构 | 状态 | 假说数 | 生成调用 | 生成输入 token | 生成输出 token | 终评调用 |','|---|---|---:|---:|---:|---:|---:|']
 for s in SYSTEMS:
  out=ROOT/'runs'/s;state=json.loads((out/'STATUS.json').read_text())
  final=json.loads((out/'FINAL.json').read_text()) if (out/'FINAL.json').exists() else {'hypotheses':[]}
  ck=ROOT/'runs'/(s+'_evaluation')/'CHECKS.json';checks=json.loads(ck.read_text()) if ck.exists() else {'checks':[]}
  raw_checks=json.loads(json.dumps(checks))
  for c in checks['checks']:
   b=broad_by.get((s,c['hypothesis_id']))
   if b:
    c['initial_prior_work_status']=c['prior_work_status'];c['initial_prior_work_reason']=c['prior_work_reason'];c['initial_sources']=c['sources']
    c.update(prior_work_status=b['prior_work_status'],prior_work_reason=b['reason'],sources=b['sources'],prior_work_evidence_scope='shared_prior_work_evaluation')
   a=audit_by.get((s,c['hypothesis_id']))
   if a:
    c['initial_coherence_status']=c['coherence_status'];c['initial_coherence_reason']=c['coherence_reason'];c['coherence_status']=a['coherence_status'];c['coherence_reason']=a['reason'];c['controller_audit']=True
  gen=accounting(out);evaluation=accounting(ck.parent)
  all_results[s]={'state':state,'final':final,'checks':checks,'raw_terminal_checks':raw_checks,'generation_usage':gen,'evaluation_usage':evaluation}
  lines.append(f"| {s} | {state['status']} | {len(final['hypotheses'])} | {gen['settled_calls']} | {gen['input_tokens']:,} | {gen['output_tokens']:,} | {evaluation['settled_calls']} |")
 lines+=['','调用按实际成功或截断响应结算记录统计，含定义服务和恢复尝试；缓存复用不重复计入。失败及未返回请求的实际计费未知。各架构发言、评审和工具选择不同，实际资源不是等额。','']
 for s,data in all_results.items():
  lines+=['## '+s,'',data['final'].get('summary',''),'']
  check_by={c['hypothesis_id']:c for c in data['checks']['checks']}
  for h in data['final']['hypotheses']:
   c=check_by.get(h['id'],{})
   lines+=['### '+h['id']+' '+h['title'],'','**假说机制。** '+h['mechanism'],'','**关系或推导。** '+h['equations_or_derivation'],'','**实测支持。** '+h['measured_support'],'','**适用假设。** '+'；'.join(h['assumptions']),'','**区别后果。** '+h['distinct_prediction'],'','**竞争解释。** '+h['alternatives'],'','**原始出处。** '+h['trajectory_origin'],'','**独立终评。** '+c.get('prior_work_status','pending')+'；'+c.get('coherence_status','pending')+'。'+c.get('prior_work_reason','')+' '+c.get('coherence_reason',''),'']
   for cited in c.get('sources',[]):
    source_folder=c.get('prior_work_evidence_scope',s+'_evaluation')
    p=ROOT/'runs'/source_folder/'knowledge/accepted'/(cited['source_id']+'.json')
    if p.exists():
     source=json.loads(p.read_text());lines+=['- ['+source['title']+']('+source['url']+')：'+cited['relation']]
   lines+=['']
 lines+=['## 补充执行与检查校正','','AI-Scientist-v2 第二节点最初被 AST 检查误拦于 matplotlib.use("Agg")。修正这个检查后，在服务器原样执行已保存 node_1.py，退出码 0，无新模型调用；原始冻结结果保持不变。补充 stdout 和代码哈希见 controller_only/server_node_verification/EXECUTION.json。该补充进一步发现八状态块内至少三次驱动反转，因此八个事件的重复不能等同于一个驱动周期。','','EvoScientist H3 的独立终评原给 no_obvious_error；控制端复算指出把最大切换位置 5.9 cm 当作当前驱动振幅，以及把状态块重复直接定义为 period-1，均超出给定记录。原终评原样保留，报告采用 controller_only/CONTROLLER_AUDIT.json 中的校正。','','初始终评对相似研究的判断偏重装置细节，随后以同一历史时间边界共享检索并复核研究方向；报告采用 BROAD_SCOPE_AUDIT.json 的判断，并保留初判。','', '## 证据和边界','','原始回复、工具记录、原版讨论/计算结果、假说出处和冻结清单均保存在 runs/。FINAL.json 是各架构实际轨迹的统一提取；独立终评单独保存且未返回生成系统。no_close_work_found 仅表示本次有界检索未找到高度相近工作；实验验证和世界新颖性仍须分别建立。','', '同一个小型场景、短程和不同 native 角色数支持比较具体内容与开销，架构整体优劣需要重复运行和更广场景。']
 (ROOT/'ALL_RESULTS.json').write_text(json.dumps(all_results,indent=2,ensure_ascii=False))
 (ROOT/'RESULTS_CN.md').write_text('\n'.join(lines)+'\n')
 status={'status':'complete' if all(d['state']['status']=='complete' for d in all_results.values()) and broad['checks'] else 'incomplete','systems':{s:d['state']['status'] for s,d in all_results.items()},'total_hypotheses':sum(len(d['final']['hypotheses']) for d in all_results.values()),'generation_totals':{k:sum(d['generation_usage'][k] for d in all_results.values()) for k in ['settled_calls','input_tokens','output_tokens','reasoning_tokens']},'evaluation_totals':{k:sum(d['evaluation_usage'][k] for d in all_results.values())+accounting(broad_path.parent)[k] for k in ['settled_calls','input_tokens','output_tokens','reasoning_tokens']}}
 (ROOT/'STATUS.json').write_text(json.dumps(status,indent=2));print(json.dumps(status,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
