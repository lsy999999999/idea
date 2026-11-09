"""Create a clean experiment folder for a different API/model; never reuse prior outputs."""
from pathlib import Path
import argparse,json,shutil
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--model',required=True);p.add_argument('--base-url',required=True);p.add_argument('--api-style',choices=['chat','responses'],default='chat');p.add_argument('--reasoning-effort',default=None);p.add_argument('--knowledge',choices=['online','closed'],default='online');a=p.parse_args()
if a.output.exists():p.error('Output already exists; choose a new folder to preserve earlier experiments')
a.output.mkdir(parents=True)
for folder in ['cases','runtime']:
 shutil.copytree(ROOT/folder,a.output/folder,ignore=shutil.ignore_patterns('__pycache__','library','runs','researchers','api_researchers'))
for name in ['comparison_config.json','systems_manifest.json','candidate_sources.json','SOURCE_NOTES_CN.md','PROTOCOL_CN.md']:
 shutil.copy2(ROOT/name,a.output/name)
cfg=json.loads((ROOT/'model_config.json').read_text());cfg.update(model=a.model,api_style=a.api_style,reasoning_effort=a.reasoning_effort,credential_source='environment',base_url=a.base_url,api_key_env='RESEARCH_MODEL_API_KEY')
cfg['knowledge']=a.knowledge
cfg['preserve_reasoning_items']=a.api_style=='responses'
# Historical inputs remain frozen; only NEW run copies receive their actual access policy.
policy=('Read actual public scientific sources via the broker and inspect the complete CSV using tools. Source identity is visible. This is a new interface-enabled run, not the historical closed-corpus comparison.' if a.knowledge=='online' else 'Use the supplied source corpus only. Online search is disabled explicitly; full CSV tools remain available.')
for case in ['wave','optical']:
 for path in [a.output/'cases'/case/'dossier.json',a.output/'runtime/ours_source/learning_lab/scenarios'/(case+'.md')]:
  data=json.loads(path.read_text());data['retrieval_policy']=policy;path.write_text(json.dumps(data,ensure_ascii=False,indent=2))
(a.output/'model_config.json').write_text(json.dumps(cfg,indent=2))
(a.output/'REPLAY_STATUS.json').write_text(json.dumps({'status':'prepared_no_calls','origin':str(ROOT),'model':a.model,'source_inputs':'measurements unchanged; source-access policy updated only in new copies','knowledge':a.knowledge,'comparability':'Other adapters do not automatically gain the same tools; align access before method comparison','results_and_memory_reused':False},indent=2))
print(a.output.resolve())
