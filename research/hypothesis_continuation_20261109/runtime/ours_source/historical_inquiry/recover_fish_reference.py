"""One audited metadata-only recovery; no model call or scientific text rewrite."""
import copy
import hashlib
import json
from pathlib import Path

from fish_pilot import FishPilot, load, save
from fish_materials import digest


if __name__ == '__main__':
    pilot = FishPilot()
    sid = 'r2_evidence_discuss_2'
    root = pilot.run/'stages'/sid
    if sid in pilot.state['stages']:
        raise SystemExit('Stage already committed; no recovery needed')
    prompt = (root/'attempt-001/prompt.txt').read_text()
    context = json.loads(prompt.split('INPUTS:\n', 1)[1])
    raw_path = root/'attempt-002/final.txt'
    raw = load(raw_path)
    result = copy.deepcopy(raw)
    wrong = str((root/'result.json').resolve())
    correct = context['verification_report_path']
    if correct not in {r['report_path'] for r in pilot.evidence.reports()}:
        raise ValueError('Replacement report was not supplied and authenticated')
    changes = []
    for i, note in enumerate(result['memory_notes']):
        for j, source in enumerate(note['sources']):
            if source == wrong:
                note['sources'][j] = correct
                changes.append({'json_pointer': f'/memory_notes/{i}/sources/{j}',
                                'before': wrong, 'after': correct})
    if not changes:
        raise ValueError('Exact self-reference problem not found')
    # Verify every difference is exactly the declared reference substitution.
    reconstructed = copy.deepcopy(result)
    for c in changes:
        _, _, i, _, j = c['json_pointer'].split('/')
        reconstructed['memory_notes'][int(i)]['sources'][int(j)] = wrong
    assert reconstructed == raw
    record = {'kind': 'controller_reference_alias_only', 'raw_response': str(raw_path.resolve()),
              'raw_sha256': digest(raw_path), 'changes': changes,
              'reason': 'Unsaved self-result is not independent evidence. This response discusses the supplied internal report; resolve the mistaken self-reference to that report.',
              'scientific_content_changed': False, 'additional_model_call': False}
    result['controller_reference_repair'] = record
    role = context['researcher']
    pilot.validate(sid, role, result, context, notes=True, initial=False)
    path = root/'result.json'
    save(path, result)
    pilot.memory.commit(role, pilot.task_id, sid, path)
    pilot.questions.accept(sid, role, result, path, context['question_state'])
    pilot.evidence.observe(sid, role, result, path)
    pilot.state['stages'][sid] = {'input_sha256': hashlib.sha256(prompt.encode()).hexdigest(),
                                'output_sha256': digest(path)}
    save(pilot.state_path, pilot.state)
    save(pilot.run/'recovery/REFERENCE_REPAIR.json', record)
    print(json.dumps(record, ensure_ascii=False))
