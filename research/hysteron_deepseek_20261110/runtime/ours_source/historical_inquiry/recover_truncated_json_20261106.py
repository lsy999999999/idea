"""Audited admission of an otherwise complete response missing one final root brace."""
import copy
import hashlib
import json
from fish_inquiry import InquiryPilot, ExistingPilot, admit_reference_layout, load, save
from fish_materials import digest
from note_dependencies import prepare_dependencies

pilot = InquiryPilot(run_id='inquiry_v2_live_20261106_002')
sid = '01_initial_1_learn_0'
root = pilot.run/'stages'/sid
assert sid not in pilot.state['stages']
raw_path = root/'attempt-001/final.txt'
text = raw_path.read_text()
raw = json.loads(text.rstrip()+'}')
prompt = (root/'attempt-001/prompt.txt').read_text()
context = json.loads(prompt.split('INPUTS:\n',1)[1])
answer = ExistingPilot.admit_bookkeeping(copy.deepcopy(raw), researcher=True)
answer = admit_reference_layout(answer, sid, pilot.broker)
receipt = {'raw_response': str(raw_path.resolve()), 'raw_sha256': digest(raw_path),
           'edit': {'offset': len(text.rstrip()), 'append': '}'},
           'scientific_content_changed': False, 'new_model_call': False}
answer['controller_truncated_json_recovery'] = receipt
alias_changes = []
for claim in answer['evidence_claims']:
    basis = claim['basis']
    if 'measurement_context' in basis['source_ids']:
        before = copy.deepcopy(basis)
        basis['source_ids'].remove('measurement_context')
        basis.setdefault('measurement_sources', []).append('measurement_context')
        alias_changes.append({'claim_id': claim['id'], 'before': before, 'after': copy.deepcopy(basis)})
inherited = {item['note']['key']: item['note'] for item in context['memory']['retrieved']}
note_changes = []
for note in answer.get('memory_notes', []):
    before = list(note['sources'])
    note['sources'] = ['measurements.json' if source == 'measurement_context' else source for source in note['sources']]
    previous = inherited.get(note['key'])
    if previous and note.get('revision_reason'):
        # Preserve inherited correction/report provenance, not added scientific evidence.
        reports = [source for source in previous['sources'] if source.endswith('/result.json')]
        note['sources'].extend(source for source in reports if source not in note['sources'])
    if note['sources'] != before:
        note_changes.append({'key': note['key'], 'before': before, 'after': note['sources']})
receipt['measurement_alias_changes'] = alias_changes
receipt['note_provenance_restoration'] = note_changes
role = context['researcher']
pilot.validate(sid, role, answer, context, notes=True, initial=False)
pending = {'input_sha256': hashlib.sha256(prompt.encode()).hexdigest(),
           'note_dependencies': prepare_dependencies(pilot, answer, context)}
path = root/'result.json'
save(path, answer)
pending['output_sha256'] = digest(path)
save(root/'admission.json',pending)
pilot.commit_stage(sid,role,answer,path,context,False,pending)
save(pilot.run/'recovery/TRUNCATED_JSON_RECOVERY.json',receipt)
print(json.dumps(receipt,ensure_ascii=False))
