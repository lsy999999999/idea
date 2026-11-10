from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parent
G=R/'runtime/ours_source/runs/hypothesis_development_hysteron_generation'
s=json.loads((G/'learning_state.json').read_text())
rows=[]
for stage,meta in s['stages'].items():
 p=G/'stages'/stage/'api_v2/workspace/result.json'
 if not p.exists():continue
 d=json.loads(p.read_text())
 rows.append({'stage':stage,'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'summary':d.get('summary'),'development_step':d.get('development_step'),'hypothesis_updates':d.get('hypothesis_updates'),'content_comparison':d.get('content_comparison'),'next_research_move':d.get('next_research_move'),'expertise_request':d.get('expertise_request')})
(R/'TRAJECTORY_INDEX.json').write_text(json.dumps({'status':s.get('status'),'stages':rows},ensure_ascii=False,indent=2))
print('Indexed accepted stages',len(rows))
