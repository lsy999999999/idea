from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
parent=json.loads((R/'PARENT_FREEZE.json').read_text())
report={'parent_files':len(parent),'parent_changed':[p for p,h in parent.items() if not Path(p).exists() or sha(p)!=h]}
G=R/'runtime/ours_source/runs/hypothesis_development_hysteron_generation'
if (G/'GENERATION_FREEZE.json').exists():
 f=json.loads((G/'GENERATION_FREEZE.json').read_text())
 report['generation_files']=len(f['files']);report['generation_changed']=[p for p,h in f['files'].items() if not Path(p).exists() or sha(p)!=h]
 report['memory_files']=len(f['memory_files']);report['memory_changed']=[p for p,h in f['memory_files'].items() if not Path(p).exists() or sha(p)!=h]
report['usage']={str(p.relative_to(R)):json.loads(p.read_text()) for p in (R/'runs').rglob('usage.json')}
(R/'AUDIT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False))
