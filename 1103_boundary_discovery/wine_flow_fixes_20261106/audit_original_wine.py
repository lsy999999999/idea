"""Read-only diagnosis of the original wine run using the new process contracts."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent/'src'))
from discover import read, write
from learning_memory import digest
from learning_support import calculation, material_coverage, QuestionState

ORIGINAL = Path('/Applications/ideas/1103_boundary_discovery')
RUN = ORIGINAL/'runs/e2e_eval_20261106_wine'
EVAL = ORIGINAL/'evaluation_20261106_wine'


def main():
    error = read(EVAL/'OBSERVER_ERROR_SEALED.json')
    assert digest(error['source']) == error['source_sha256']
    contrast = calculation({'kind': 'calculation', 'bindings': {'ratings': [[6,5],[8,7]]},
                            'expression': 'ratings[:,1]-ratings[:,0]', 'expected': [2,2]})
    sample = calculation({'kind': 'calculation', 'bindings': {'ratings': [[6,5],[8,7]]},
                          'expression': 'ratings[1,:]-ratings[0,:]', 'expected': [2,2]})
    assert contrast['actual'] == [-1, -1] and contrast['matches_expected'] is False
    assert sample['actual'] == [2, 2] and sample['matches_expected'] is True
    roles = ['wine_chemist_eval', 'measurement_theorist_eval']
    state = QuestionState(ROOT/'diagnostic_question_state', roles)
    for i, role in enumerate(roles):
        source = RUN/f'stages/02_initial_{i}/native-001/workspace/result.json'
        state.accept('initial_'+str(i), role, read(source), source, initial=True)
    packet = state.packet('return_1', roles[1])
    returned = read(RUN/'stages/05_return_1/native-001/workspace/result.json')
    assert returned['question_before'] != packet['self']['question']
    assert returned['question_before'] == packet['peer_questions'][0]['question']
    try:
        state.validate('return_1', roles[1], returned, packet)
    except ValueError as error:
        rejected = str(error)
    else:
        raise AssertionError('Old ambiguous before/after schema must be rejected')
    source_result = read(RUN/'stages/01_materials/native-001/workspace/result.json')
    copied = json.loads(json.dumps(source_result))
    for i, source in enumerate(copied['sources']):
        original = Path(source['local_path'])
        target = ROOT/'diagnostic_source_copies'/f'{i}.txt'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(original.read_bytes())
        source['local_path'] = str(target)
    coverage = material_coverage(copied)
    assert coverage['status'] == 'incomplete'
    write(ROOT/'ORIGINAL_FAILURE_REPRODUCTION.json', {
        'rater_contrast': contrast, 'sample_contrast': sample,
        'own_question': packet['self']['question'], 'misattributed_peer_question': returned['question_before'],
        'old_question_schema_rejected': rejected, 'material_coverage': coverage,
        'scope': 'Controller diagnosis/recomputation of an already known defect, not a live model independently detecting it.',
        'old_run_modified': False, 'delivered_to_old_generation': False})
    print('Original arithmetic, attribution and source-coverage failures reproduced.')


if __name__ == '__main__':
    main()
