"""Bounded follow-up correcting the final check's similarity threshold."""
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / 'src'))
from discover import read, stage_run, write
from idea_check import CHECKER_PROMPT, POLICY, validate_checks

run = Path(__file__).resolve().parent
ideas_path = run / 'ideas.json'
path, result = stage_run(
    run, 'check_calibrated', 'idea_check_agent',
    CHECKER_PROMPT + '\nFollow CHECK_CALIBRATION.md for this bounded reassessment. '
    'Save the source abstracts/excerpts used in a local SOURCES.md, with actual URLs. '
    'Do not spend time on exhaustive full-text retrieval.',
    [POLICY, ideas_path, run / 'check_report.json', run / 'CHECK_CALIBRATION.md'],
    'gpt-6-luna', 'high', 600,
)
checks = validate_checks(result, read(ideas_path)['ideas'])
write(run / 'check_report_calibrated.json', {
    'ideas_path': str(ideas_path), 'check_result_path': str(path),
    'supersedes': str(run / 'check_report.json'),
    'checks': checks, 'searches': result['searches'],
})
state = read(run / 'idea_state.json')
state['initial_check_report'] = str(run / 'check_report.json')
state['check_report'] = str(run / 'check_report_calibrated.json')
write(run / 'idea_state.json', state)
print('Completed calibrated final check.', flush=True)
