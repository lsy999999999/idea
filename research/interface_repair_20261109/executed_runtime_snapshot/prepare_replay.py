"""Create a clean experiment folder for a different API/model; never reuse prior outputs."""
from pathlib import Path
import argparse,json,shutil
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--model',required=True);p.add_argument('--base-url',required=True);p.add_argument('--api-style',choices=['chat','responses'],default='chat');p.add_argument('--reasoning-effort',default=None);a=p.parse_args()
if a.output.exists():p.error('Output already exists; choose a new folder to preserve earlier experiments')
a.output.mkdir(parents=True)
for folder in ['cases','runtime']:
 shutil.copytree(ROOT/folder,a.output/folder,ignore=shutil.ignore_patterns('__pycache__','library','runs','researchers','api_researchers'))
for name in ['comparison_config.json','systems_manifest.json','candidate_sources.json','SOURCE_NOTES_CN.md','PROTOCOL_CN.md']:
 shutil.copy2(ROOT/name,a.output/name)
cfg=json.loads((ROOT/'model_config.json').read_text());cfg.update(model=a.model,api_style=a.api_style,reasoning_effort=a.reasoning_effort,credential_source='environment',base_url=a.base_url,api_key_env='RESEARCH_MODEL_API_KEY')
(a.output/'model_config.json').write_text(json.dumps(cfg,indent=2))
(a.output/'REPLAY_STATUS.json').write_text(json.dumps({'status':'prepared_no_calls','origin':str(ROOT),'model':a.model,'source_inputs':'copied byte-for-byte','results_and_memory_reused':False},indent=2))
print(a.output.resolve())
