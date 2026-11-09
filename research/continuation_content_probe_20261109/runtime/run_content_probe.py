"""Explicit shortened content diagnostic, not the complete native inquiry controller."""
from pathlib import Path
import json
import subprocess
import sys
import time
from run_ours import StageAdapter

ROOT = Path(__file__).resolve().parents[1]
cfg = json.loads((ROOT/'model_config.json').read_text())
log = (ROOT/'gateway.log').open('w')
gateway = subprocess.Popen([sys.executable, str(ROOT/'runtime/model_gateway.py')], stdout=log, stderr=subprocess.STDOUT)
endpoint = ROOT/'gateway_endpoint.json'
try:
    for _ in range(100):
        if endpoint.exists():
            break
        if gateway.poll() is not None:
            raise RuntimeError('Gateway startup failed')
        time.sleep(.1)
    else:
        raise TimeoutError('Gateway startup timeout')
    adapter = StageAdapter(ROOT, 'optical', 'generation', cfg, 'closed')
    base = [ROOT/'cases/optical/dossier.json', ROOT/'inputs/unaccepted_draft.json',
            *sorted((ROOT/'inputs').glob('source_*.json'))]
    previous = []
    instructions = [
        ('01_develop', 'content_researcher',
         'Continue the supplied actual unfinished researcher draft into scientific content. '
         'Develop one or two specific explanatory hypotheses with explicit assumptions, a small derivation or worked example, '
         'a conditional prediction that distinguishes alternatives, and the remaining gap. Use full-CSV calculations if useful. '
         'You can reason conditionally without a completed proof or missing apparatus metadata. '
         'Inspect what the complete data actually support; distinguish unit-vector normalization from fixed direction. '
         'Do not claim the source paper results as new. Do not spend turns on broad prerequisite searching. '
         'Return hypotheses:[{id,question,assumptions,derivation,prediction,alternative,evidence_status,remaining_gap}].'),
        ('02_critic', 'content_critic',
         'Review the actual previous development for concrete mathematical/logical/extraction errors and whether its predictions '
         'distinguish the stated alternatives. Recompute if needed. Preserve coherent conditional hypotheses and distinguish '
         'missing evidence from an error. Return findings:[{id,quote,status:correct/needs_correction/unresolved,reason,consequence}]. '
         'Propose no replacement scientific agenda.'),
        ('03_revise', 'content_researcher',
         'Respond to every actual critic finding, accepting justified corrections and rebutting invalid ones. '
         'Return verification_responses:[{finding_id,stance:accept/rebut/unresolved,reason}], '
         'final_hypotheses:[{id,question,assumptions,derivation,prediction,alternative,evidence_status,remaining_gap}], '
         'and reasoning_changes describing which premise, relation and downstream question changed or remained. '
         'Keep partial branches and explicitly separate observations, learning examples and new conditional proposals.')
    ]
    for sid, role, prompt in instructions:
        path, result = adapter(adapter.run, sid, role,
                               prompt + ' Keep the scientific text concise. Empty artifacts is allowed; your exact summary will be saved. '
                               'No native memory_notes, question_state or hypothesis_updates contract applies in this explicit content-only diagnostic.',
                               [*base, *previous], cfg['model'], cfg['reasoning_effort'], 240)
        previous.append(path)
    (ROOT/'result.json').write_text(json.dumps({'scope':'shortened seeded content-only diagnostic; not full native pipeline',
        'stages':[str(p) for p in previous], 'final':json.loads(previous[-1].read_text())},ensure_ascii=False,indent=2))
    status = {'status':'complete', 'complete_native_workflow':False}
except BaseException as exc:
    status = {'status':'failed', 'error':str(exc), 'complete_native_workflow':False}
finally:
    gateway.terminate()
    gateway.wait(timeout=10)
    log.close()
    if endpoint.exists() and json.loads(endpoint.read_text()).get('pid') == gateway.pid:
        endpoint.unlink()
(ROOT/'STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2))
print(json.dumps(status,ensure_ascii=False),flush=True)
