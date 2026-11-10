"""Create a fresh run from reviewed code and empirical workbook cells only."""
from pathlib import Path
import csv,json,hashlib,shutil
ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent/'hypothesis_development_20261110'
ORIG=ROOT.parent/'scenario_selection_20261110/controller_only'
def write(p,x):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2))
if (ROOT/'runtime').exists():raise SystemExit('Preparation is immutable; create another experiment to prepare again')
freeze={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in BASE.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
write(ROOT/'PARENT_FREEZE.json',freeze)
shutil.copytree(BASE/'runtime',ROOT/'runtime',ignore=shutil.ignore_patterns('__pycache__','runs','api_researchers','evaluations','*.pyc'))
cfg=json.loads((BASE/'model_config.json').read_text())
cfg.update(model='deepseek-flash',api_style='chat',base_url='https://api.deepseek.com',reasoning_effort='high',preserve_reasoning_items=False,credential_source='private_file',credential_file='/Users/LSY/.config/ideas/credentials/deepseek.key',chat_reasoning_parameter='reasoning_effort',thinking_enabled=True,hypothesis_rounds=6,max_completion_tokens=32768,researchers=[['domain_scientist','弹性机构、刚体力学与准静态实验'],['theory_scientist','非线性动力学、迟滞与统计物理']])
write(ROOT/'model_config.json',cfg)
for name in ['run.py','run_ours.py','evaluate_frozen.py','prepare_case_sources.py']:
 p=ROOT/'runtime'/name;t=p.read_text().replace("choices=['optical','wave']","choices=['optical','wave','hysteron']").replace("choices=['wave','optical']","choices=['wave','optical','hysteron']")
 if name=='run_ours.py':t=t.replace('parallel_tool_calls=False,max_tokens=12000','parallel_tool_calls=False,max_tokens=self.cfg.get(\'max_completion_tokens\',12000)')
 p.write_text(t)
print('Fresh runtime copied; source hashes preserved')
