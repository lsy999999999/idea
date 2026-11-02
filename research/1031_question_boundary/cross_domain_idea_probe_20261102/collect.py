"""Compact inspection of completed replies only; never read working drafts."""
import json
import sys
import harness as h

for run in sorted((h.ROOT/'runs').iterdir()):
    s=h.state(run)
    if not s['final']:continue
    f=s['final'];idea=f.get('final_idea') or {}
    first=s['replies'][0]['reply']
    row=dict(run=run.name,initial_candidates=[dict(id=x.get('id'),title=x.get('title'),claim=x.get('new_claim')) for x in first.get('candidates',[])],selected_id=first.get('selected_id'),status=f.get('status'),title=idea.get('title'),question=idea.get('question'),claim=idea.get('new_claim'),prediction=idea.get('testable_prediction'),falsifier=f.get('falsifier'),next_test=f.get('minimum_next_test'),evidence_level=f.get('evidence_level'),known=f.get('what_is_known'),changed=f.get('what_changed'),novelty=f.get('novelty_status'),recognition=first.get('recognition'),tool_statuses=[dict(id=t['id'],type=t['type'],status=t['result']['status']) for t in s['tools']])
    if len(sys.argv)>1 and sys.argv[1] not in run.name:continue
    print(json.dumps(row,ensure_ascii=False))
