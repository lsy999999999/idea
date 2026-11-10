"""Execute one unchanged, previously ignored actor plan AFTER generation; no feedback."""
from pathlib import Path
import json
from analysis_executor import AnalysisExecutor
from fish_materials import Broker,CASE,digest
from prepare import save

here=Path(__file__).resolve().parent
run=CASE/'runs/inquiry_v2_live_20261106_002'
freeze=json.loads((run/'GENERATION_FREEZE.json').read_text())
assert all(digest(p)==h for p,h in freeze['files'].items())
source=run/'stages/r1_exchange_1/result.json'
plan=json.loads(source.read_text())['analysis_plan']
root=here/'live_postfreeze_diagnostics_20261106'
result=AnalysisExecutor(Broker(CASE),root/'analysis').execute(plan,'unchanged_sensorimotor_plan')
save(root/'RECEIPT.json',{'generation_freeze_sha256':digest(run/'GENERATION_FREEZE.json'),
    'source_result':str(source.resolve()),'source_result_sha256':digest(source),
    'plan_changed':False,'researcher_received_result':False,'model_calls':0,
    'purpose':'Post-generation controller diagnosis of an ignored top-level analysis plan; not evidence used to form the frozen ideas.',
    'result':result})
assert all(digest(p)==h for p,h in freeze['files'].items())
print(json.dumps(result['result'],ensure_ascii=False,indent=2))
