"""Create a clean experiment folder for a different API/model; never reuse prior outputs."""
from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'runtime/ours_source/historical_inquiry'))
from case_access import CASE_RULES, actor_brief, locked_policy, assert_measurements
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--model',required=True);p.add_argument('--base-url',required=True);p.add_argument('--api-style',choices=['chat','responses'],default='chat');p.add_argument('--reasoning-effort',default=None);p.add_argument('--knowledge',choices=['online','closed'],default='online');a=p.parse_args()
if a.output.exists():p.error('Output already exists; choose a new folder to preserve earlier experiments')
a.output.mkdir(parents=True)
for folder in ['cases','runtime']:
 shutil.copytree(ROOT/folder,a.output/folder,ignore=shutil.ignore_patterns('__pycache__','library','runs','researchers','api_researchers'))
for name in ['comparison_config.json','systems_manifest.json','candidate_sources.json','SOURCE_NOTES_CN.md','PROTOCOL_CN.md']:
 shutil.copy2(ROOT/name,a.output/name)
comparison=json.loads((ROOT/'comparison_config.json').read_text())
(a.output/'comparison_config.json').write_text(json.dumps({'status':'prepared_no_calls','origin':str(ROOT),
 'fairness_targets':comparison.get('fairness_targets',comparison.get('fairness',{})),
 'observed_fairness':None,'full_matched_reproduction_complete':False,'knowledge':a.knowledge},indent=2))
cfg=json.loads((ROOT/'model_config.json').read_text());cfg.update(model=a.model,api_style=a.api_style,reasoning_effort=a.reasoning_effort,credential_source='environment',base_url=a.base_url,api_key_env='RESEARCH_MODEL_API_KEY')
cfg['knowledge']=a.knowledge
cfg['preserve_reasoning_items']=a.api_style=='responses'
cfg['historical_lock']=True
# Historical inputs remain frozen; only NEW run copies receive their actual access policy.
controller=a.output/'controller_only';controller.mkdir()
boundaries={}
for case in ['wave','optical']:
 boundaries[case]=locked_policy(case)
 assert_measurements(case,a.output/'cases'/case/'measurements.csv')
 original=json.loads((ROOT/'cases'/case/'dossier.json').read_text())
 origin=original.get('source',{'title':CASE_RULES[case]['titles'][0],'doi':CASE_RULES[case]['dois'][0],'published':CASE_RULES[case]['before']})
 (controller/(case+'_origin.json')).write_text(json.dumps(origin,ensure_ascii=False,indent=2))
 for path in [a.output/'cases'/case/'dossier.json',a.output/'runtime/ours_source/learning_lab/scenarios'/(case+'.md')]:
  data=actor_brief(case,json.loads(path.read_text()));path.write_text(json.dumps(data,ensure_ascii=False,indent=2))
(controller/'HISTORICAL_BOUNDARIES.json').write_text(json.dumps(boundaries,ensure_ascii=False,indent=2))
shutil.move(a.output/'PROTOCOL_CN.md',controller/'HISTORICAL_ADAPTER_PROTOCOL.md')
(a.output/'PROTOCOL_CN.md').write_text('''# 历史盲测硬约束

原论文身份、解释和结论不进入科研 agent 输入。只供应已登记哈希的原始测量 CSV、数据字段和测量概览。

- 光学案例：只允许出版日期严格早于 2026-08-12 的独立资料。
- 机械案例：只允许出版日期严格早于 2026-10-14 的独立资料。
- 原论文 DOI、标题、已知镜像/版本及指向它们的来源关系由控制端代码固定排除；配置不能取消。
- 同日、之后、日期不明的资料拦截；正文另核对自己的出版/版本日期。
- 检索回复、分页原文、工具缓存、模型输入均重新核验。旧研究记忆与已读原文的会话不复用。
- 未经筛选的 shell/服务器 agent 入口停用；已支持受控 API 与无外部工具的讨论适配器。

这只约束实验供应与检索信息；不声称排除了模型预训练知识。旧有结果保持原样，不能作为本协议下的盲测结果。
''')
(a.output/'model_config.json').write_text(json.dumps(cfg,indent=2))
(a.output/'REPLAY_STATUS.json').write_text(json.dumps({'status':'prepared_no_calls','origin':str(ROOT),'model':a.model,'source_inputs':'registered raw measurements unchanged; originating-study identity and explanations hidden','knowledge':a.knowledge,'historical_lock':True,'comparability':'Only screened API and closed discussion adapters may run; unrestricted shell adapters are blocked','results_and_memory_reused':False},indent=2))
print(a.output.resolve())
