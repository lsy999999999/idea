"""Retain the actual terminal checker; downgrade unsupported certainty, never invent evidence."""
import copy,json,sys
from pathlib import Path
from prepare import PROJECT,save
from final_evaluation import file_hash
sys.path.insert(0,str(PROJECT/'src'))
from idea_check import validate_checks,SCHEMA_VERSION

run=Path(__file__).resolve().parent/'cases/fish_001/runs/inquiry_v2_live_20261106_002'
root=run/'evaluation'
raw=root/'stages/check/attempt-001/workspace/result.json'
ideas=root/'ideas.json'
original=json.loads(raw.read_text())
report=copy.deepcopy(original)
changes=[]
for check in report['checks']:
    for comparison in check['novelty']['comparisons']:
        for key,row in comparison['facets'].items():
            if row['relation']!='UNKNOWN' and not row['evidence_ids']:
                changes.append({'idea_id':check['idea_id'],'source_id':comparison['source_id'],'facet':key,'before':row['relation'],'after':'UNKNOWN','original_reason':row['reason']})
                row['relation']='UNKNOWN'
                row['reason']='未核读实质内容且没有证据引用；原比较理由仅来自题名或元数据，故无法确认。'
    before=check['prior_work']['verdict']
    check['prior_work']['verdict']='unclear'
    check['prior_work']['reason']='实际检索留下了相邻方向的元数据记录，但没有核读并引用足够的实质内容，不能确认覆盖；补充检查因服务端401认证错误未完成。'
    if before!='unclear':changes.append({'idea_id':check['idea_id'],'field':'prior_work.verdict','before':before,'after':'unclear'})
report['summary']='冻结后的检查初稿对三个候选均报no_obvious_error；查新证据不足。控制器将无证据的确定比较降为UNKNOWN，保留全部候选为UNRESOLVED。补充检查遭遇401，实质新颖性复核未完成。'
report['controller_evidence_admission']={'source_report':str(raw.resolve()),'source_sha256':file_hash(raw),'changes':changes,
    'new_scientific_evidence_added':False,'math_judgments_unchanged':True,
    'evaluation_status':'incomplete_substantive_novelty_review','followup_failure':'HTTP 401 Unauthorized / INVALID_API_KEY; no authentication files inspected or changed',
    'scope':'Conservative controller review of an actual independent model report; not a completed model-produced evidence follow-up.'}
validate_checks(report,json.loads(ideas.read_text())['ideas'],require_claims=True)
assert not report.get('memory_notes')
path=root/'controller_review/CONSERVATIVE_REPORT.json'
save(path,report)
save(root/'ACCEPTED_CHECK.json',{'schema_version':SCHEMA_VERSION,'requested_model':'gpt-6-luna','ideas_sha256':file_hash(ideas),
    'result_path':str(path.resolve()),'result_sha256':file_hash(path),'source_model_report':str(raw.resolve()),
    'acceptance_kind':'validated_conservative_partial_report','substantive_novelty_review_complete':False})
print(json.dumps({'validation':'passed','changes':changes,'report':str(path)},ensure_ascii=False))
