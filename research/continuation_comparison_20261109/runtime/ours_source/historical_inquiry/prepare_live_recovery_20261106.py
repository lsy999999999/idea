"""Preserve the failed admission and recover its exact-input response in a new run."""
from pathlib import Path
import shutil

from fish_inquiry import InquiryPilot, load, save
from fish_materials import CASE, digest


if __name__ == '__main__':
    source = CASE/'runs/inquiry_v2_live_20261106_001'
    pilot = InquiryPilot(run_id='inquiry_v2_live_20261106_002')
    for relative in ('initial_materials.json', 'memory_retrieval/01_initial_0.json'):
        target = pilot.run/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if digest(target) != digest(source/relative):
                raise ValueError('Recovery input already differs')
        else:
            shutil.copy2(source/relative, target)
    original = source/'stages/01_initial_0/attempt-002'
    target = pilot.run/'stages/01_initial_0/attempt-001'
    if not target.exists():
        shutil.copytree(original, target)
        audit = load(target/'execution_audit.json')
        audit.update(model_call_performed_in_this_run=False, reused_execution_from=str(original.resolve()))
        save(target/'execution_audit.json', audit)
    save(pilot.run/'recovery/REUSED_RESPONSE.json', {
        'source_run': str(source.resolve()), 'source_attempt': str(original.resolve()),
        'raw_response_sha256': digest(original/'final.txt'),
        'original_code_preserved_in': str(source/'protocol_snapshot'),
        'repair': 'Reference-layout normalization only; scientific content is unchanged.',
        'reuse_condition': 'The runner accepts this response only if the complete original prompt matches the new input, or is its schema-only repair.',
        'prior_result_committed': False,
        'tests_after_fix': {'historical_suite': 65, 'status': 'passed', 'actors': 'mocked'},
    })
    save(source/'ADMISSION_FAILURE.json', {
        'status': 'preserved_before_any_scientific_stage_commit',
        'reason': 'Measurement citation appeared in bibliographic source_ids; source-validator rejected it after local-ref repair.',
        'continued_as': str(pilot.run.resolve()),
    })
    print(pilot.run)
