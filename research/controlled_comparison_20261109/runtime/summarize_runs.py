"""Freeze and inventory actual outputs; never infer successful science from a status."""
from pathlib import Path
import json,hashlib,collections
ROOT=Path(__file__).resolve().parents[1]
summary={'systems':[],'reported_models':{},'checkpoints':{},'scope':'Measured pilot, actual spend differs; completed runner does not imply complete paper reproduction'}
models=collections.Counter()
for folder in sorted((ROOT/'runs').glob('*/*/*')):
 if not folder.is_dir() or folder.parts[-3]=='transport':continue
 case,system,phase=folder.parts[-3:];status=json.loads((folder/'STATUS.json').read_text()) if (folder/'STATUS.json').exists() else {'status':'unknown'}
 usage=json.loads((folder/'usage.json').read_text()) if (folder/'usage.json').exists() else {}
 raw_in=raw_out=0;checkpoint=[]
 for p in sorted(folder.glob('*.response.json')):
  d=json.loads(p.read_text());models[d.get('model')]+=1;u=d.get('usage') or {};raw_in+=u.get('input_tokens',u.get('prompt_tokens',0));raw_out+=u.get('output_tokens',u.get('completion_tokens',0))
  if raw_in<=100000 and raw_out<=5000:checkpoint.append(p.name)
 if usage:
  assert raw_in==usage['input_tokens'],folder
  assert raw_out==usage['output_tokens'],folder
 entry={'case':case,'system':system,'phase':phase,'status':status['status'],'error':status.get('error'),'usage':usage,'provider_usage_reconciled':True,'result':str(folder/'result.json') if (folder/'result.json').exists() else None,'artifact_files':[str(p) for p in (folder/'workspace').glob('*.md')]}
 summary['systems'].append(entry)
 if phase=='generation':summary['checkpoints'][case+'/'+system]={'budget':{'input_tokens':100000,'output_tokens':5000},'successful_responses_within_both_limits':checkpoint,'meaning':'Common budget prefix, not equal actual consumption; failed calls have unknown usage'}
 # Preserve any earlier freeze. New seal is the final artifact inventory.
 paths=[p for p in folder.rglob('*') if p.is_file() and p.name not in ['FINAL_FREEZE.json']]
 (folder/'FINAL_FREEZE.json').write_text(json.dumps({'files':{str(p.relative_to(folder)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}},indent=2))
summary['reported_models']=dict(models)
summary['totals']={key:sum(e['usage'].get(key,0) for e in summary['systems']) for key in ['calls','input_tokens','output_tokens','cached_tokens','failed_calls','usage_unknown_calls']}
(ROOT/'SUMMARY.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));print(json.dumps({'totals':summary['totals'],'statuses':[(e['case'],e['system'],e['phase'],e['status']) for e in summary['systems']]},ensure_ascii=False,indent=2))
