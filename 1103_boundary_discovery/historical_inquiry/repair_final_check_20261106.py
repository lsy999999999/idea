"""Independent terminal checker follow-up; no generation calls or memory feedback."""
import json,sys
from pathlib import Path
from prepare import PROJECT,save
sys.path.insert(0,str(PROJECT/'src'))
from discover import stage_run
from idea_check import CHECKER_PROMPT,POLICY,SCHEMA_VERSION,validate_checks
from final_evaluation import file_hash

run=Path(__file__).resolve().parent/'cases/fish_001/runs/inquiry_v2_live_20261106_002'
root=run/'evaluation'
raw=root/'stages/check/attempt-001/workspace/result.json'
ideas=root/'ideas.json'
result_path,result=stage_run(root,'check_evidence_repair','idea_check_agent',CHECKER_PROMPT+'''
This is a terminal evaluation follow-up after a frozen generation. No researcher may be called;
do not change candidate ideas, generation, source code, or researcher memory.
The first checker returned a full report but validation failed: 'a definite comparison needs
source evidence'. Its source records say metadata_only, evidence arrays are empty, yet facets
and close_direction_found make definite substantive comparisons. Preserve the first report.
Repair the EVIDENCE CONTRACT in a NEW complete report in your assigned workspace.
First inspect existing source snapshots and supplied generation_evidence.json: one 2009
animal-motion source already has a readable abstract and a dated snapshot. Read substantive
content before claiming overlap. Retain exact quotes and matching source IDs. Dates need
snapshot-backed publication_date objects as required by novelty_scope.py. If evidence does
not support a definite comparison, mark UNKNOWN, with prior verdict unclear where required;
do not invent support or treat absence of findings as novelty. Source coverage and historical
eligibility can remain unresolved. Do not reject incomplete questions for lack of experiments.
Keep the frozen historical context unchanged; later or hidden originating work cannot reject
a task-relative idea. All three no_obvious_error judgments may remain if still justified.
Use the existing limited evidence or at most a focused source read; do not restart broad searches.
Before finishing, validate the full report with the project's actual validator:
import sys,json; sys.path.insert(0,"/Applications/ideas/1103_boundary_discovery/src");
from idea_check import validate_checks
validate_checks(json.load(open(YOUR_RESULT_JSON)),json.load(open(INPUT_IDEAS_JSON))["ideas"],require_claims=True)
The exact input ideas path and source code are supplied below. Read novelty_contract.py and
novelty_scope.py only as needed to fix schema/aggregation; leave both untouched. Return no
memory_notes. Save uncertain but valid conclusions, not unsupported exact coverage.
''',[raw,ideas,root/'generation_evidence.json',POLICY,PROJECT/'src/novelty_contract.py',PROJECT/'src/novelty_scope.py'],
'gpt-6-luna','low',480)
validate_checks(result,json.loads(ideas.read_text())['ideas'],require_claims=True)
assert not result.get('memory_notes')
save(root/'ACCEPTED_CHECK.json',{'schema_version':SCHEMA_VERSION,'requested_model':'gpt-6-luna',
    'ideas_sha256':file_hash(ideas),'result_path':str(result_path.resolve()),'result_sha256':file_hash(result_path),
    'supersedes_unadmitted_report':str(raw.resolve()),'scope':'Independent terminal evidence-contract follow-up; generation unchanged.'})
print(json.dumps({'accepted':str(result_path),'checks':[(c['idea_id'],c['prior_work']['verdict'],c['math']['verdict']) for c in result['checks']]},ensure_ascii=False))
