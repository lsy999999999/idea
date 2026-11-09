"""Explicit source-layout recovery of a preserved complete actor answer."""
import copy
import hashlib
import json

from fish_inquiry import InquiryPilot, ExistingPilot, admit_reference_layout, load, save
from fish_materials import digest
from note_dependencies import prepare_dependencies


if __name__ == '__main__':
    pilot = InquiryPilot(run_id='inquiry_v2_live_20261106_002')
    sid = '01_initial_1'
    root = pilot.run/'stages'/sid
    if sid in pilot.state['stages']:
        raise SystemExit('Already recovered')
    prompt = (root/'attempt-001/prompt.txt').read_text()
    context = json.loads(prompt.split('INPUTS:\n', 1)[1])
    raw_path = root/'attempt-001/final.txt'
    raw = load(raw_path)
    answer = ExistingPilot.admit_bookkeeping(copy.deepcopy(raw), researcher=True)
    answer = admit_reference_layout(answer, sid, pilot.broker)
    windows = {item['result']['operation']['record_id'] for item in context['sampled_windows']['computed']}
    aliases = {'measurement_metadata'} | {rid+'_window' for rid in windows}
    changes = []
    for claim in answer['evidence_claims']:
        basis = claim['basis']
        moved = [source for source in basis['source_ids'] if source in aliases]
        if moved:
            before = copy.deepcopy(basis)
            basis['source_ids'] = [source for source in basis['source_ids'] if source not in moved]
            basis['measurement_sources'] = basis.get('measurement_sources', []) + moved
            changes.append({'claim_id': claim['id'], 'before': before, 'after': copy.deepcopy(basis)})
    if not changes:
        raise ValueError('Expected exact supplied aliases not found')
    inherited = {item['note']['key']: item['note'] for item in context['memory']['retrieved']}
    source_additions = []
    for note in answer.get('memory_notes', []):
        previous = inherited.get(note['key'])
        if previous and note.get('revision_reason'):
            added = [source for source in previous['sources'] if source not in note['sources']]
            note['sources'].extend(added)
            if added:
                source_additions.append({'note_key': note['key'], 'added': added,
                    'basis': 'Restore the supplied same-key correction provenance; retain all proposed sources.'})
    receipt = {'raw_response': str(raw_path.resolve()), 'raw_sha256': digest(raw_path),
               'changes': changes, 'basis': 'Exact metadata field and measured-window IDs present in this original input.',
               'memory_source_additions': source_additions,
               'scientific_content_changed': False, 'new_model_call': False}
    answer['controller_source_alias_recovery'] = receipt
    for key in raw:
        if key not in {'claims', 'evidence_claims', 'memory_notes'}:
            assert answer[key] == raw[key], key
    restored = copy.deepcopy(answer['memory_notes'])
    for note in restored:
        for change in source_additions:
            if change['note_key'] == note['key']:
                note['sources'] = [source for source in note['sources'] if source not in change['added']]
    assert restored == raw['memory_notes']
    role = context['researcher']
    pilot.validate(sid, role, answer, context, notes=True, initial=True)
    pending = {'input_sha256': hashlib.sha256(prompt.encode()).hexdigest(),
               'note_dependencies': prepare_dependencies(pilot, answer, context)}
    result_path = root/'result.json'
    save(result_path, answer)
    pending['output_sha256'] = digest(result_path)
    save(root/'admission.json', pending)
    pilot.commit_stage(sid, role, answer, result_path, context, True, pending)
    save(pilot.run/'recovery/SOURCE_ALIAS_RECOVERY.json', receipt)
    print(json.dumps(receipt, ensure_ascii=False))
