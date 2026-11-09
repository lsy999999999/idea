"""Supervised, receipt-backed metadata recovery; never repairs scientific arguments."""
import argparse
import copy
import hashlib
import json
from fish_inquiry import InquiryPilot, ExistingPilot, admit_reference_layout, load, save
from fish_materials import digest
from note_dependencies import prepare_dependencies
from isolated_cli import parse_response

parser=argparse.ArgumentParser()
parser.add_argument('stage')
parser.add_argument('--attempt',default='attempt-001')
parser.add_argument('--allow-schema-answer',action='store_true')
args=parser.parse_args()
pilot=InquiryPilot(run_id='inquiry_v2_live_20261106_002')
sid=args.stage
root=pilot.run/'stages'/sid
assert sid not in pilot.state['stages'], 'Already committed'
raw_path=root/args.attempt/'final.txt'
audit=load(raw_path.parent/'execution_audit.json')
assert audit['returncode']==0 and audit['tool_events']==0, 'Only a successful zero-tool response is eligible'
s=raw_path.read_text()
changes=[]
try:
    raw=parse_response(s)
except json.JSONDecodeError:
    raw=json.loads(s.rstrip()+'}')
    changes.append({'field':'JSON root','append':'}','offset':len(s.rstrip())})
prompt=(root/args.attempt/'prompt.txt').read_text()
actual_prompt_hash=hashlib.sha256(prompt.encode()).hexdigest()
if '\nSCHEMA REPAIR ONLY.' in prompt:
    assert args.allow_schema_answer, 'Schema answer requires explicit selection'
    prompt=prompt.split('\nSCHEMA REPAIR ONLY.',1)[0]
    assert prompt==(root/'attempt-001/prompt.txt').read_text()
context=json.loads(prompt.split('INPUTS:\n',1)[1])
role=context.get('researcher')
if not role:
    role=prompt.split('ROLE: ',1)[1].split('\n',1)[0]
researcher=role in pilot.questions.researchers
initial=sid in {f'01_initial_{i}' for i in range(3)} and researcher
answer=ExistingPilot.admit_bookkeeping(copy.deepcopy(raw),researcher,context.get('targets') if role=='internal_evidence_verifier' else None)
if researcher:
    answer=admit_reference_layout(answer,sid,pilot.broker)
if isinstance(answer.get('summary'),list) and all(isinstance(v,str) for v in answer['summary']):
    changes.append({'field':'summary','before':answer['summary'],'operation':'join unchanged strings with newline'})
    answer['summary']='\n'.join(answer['summary'])
aliases={'measurement_context','measurement_metadata'}
if 'measurement_metadata' in context:
    aliases.add('measurements')
if 'sampled_windows' in context:
    aliases.add('sampled_windows')
if 'sampled_windows' in context:
    aliases.update(v['result']['operation']['record_id']+'_window' for v in context['sampled_windows']['computed'])
for claim in answer.get('evidence_claims',[]):
    basis=claim['basis']
    moved=[source for source in basis['source_ids'] if source in aliases]
    if moved:
        before=copy.deepcopy(basis)
        basis['source_ids']=[source for source in basis['source_ids'] if source not in moved]
        basis['measurement_sources']=basis.get('measurement_sources',[])+moved
        changes.append({'claim_id':claim['id'],'field':'measurement citation layout','before':before,'after':copy.deepcopy(basis)})
inherited={v['note']['key']:v['note'] for v in context.get('memory',{}).get('retrieved',[])}
for note in answer.get('memory_notes',[]):
    before=list(note['sources'])
    note['sources']=['measurements.json' if v in aliases else v for v in note['sources']]
    previous=inherited.get(note['key'])
    if previous and not note.get('revision_reason'):
        uses=[u for u in answer.get('memory_use',[]) if u.get('key')==note['key'] and isinstance(u.get('used_for'),str)]
        if len(uses)==1:
            note['revision_reason']=uses[0]['used_for']
            changes.append({'note_key':note['key'],'field':'revision_reason','copied_verbatim_from':'memory_use.used_for','value':note['revision_reason']})
    if previous and note.get('revision_reason'):
        reports=[v for v in previous['sources'] if v.endswith('/result.json')]
        note['sources'].extend(v for v in reports if v not in note['sources'])
    if before!=note['sources']:
        changes.append({'note_key':note['key'],'field':'sources','before':before,'after':note['sources'],'scope':'exact metadata alias or supplied same-key correction provenance'})
receipt={'raw_response':str(raw_path.resolve()),'raw_sha256':digest(raw_path),'changes':changes,
         'scientific_content_changed':False,'new_model_call':False,
         'raw_scientific_text_preserved':True,'selected_attempt':args.attempt,'selected_answer_prompt_sha256':actual_prompt_hash}
answer['controller_supervised_layout_recovery']=receipt
pilot.validate(sid,role,answer,context,notes=True,initial=initial)
pending={'input_sha256':hashlib.sha256(prompt.encode()).hexdigest(),'note_dependencies':prepare_dependencies(pilot,answer,context)}
path=root/'result.json'
save(path,answer)
pending['output_sha256']=digest(path)
save(root/'admission.json',pending)
pilot.commit_stage(sid,role,answer,path,context,initial,pending)
save(pilot.run/'recovery'/('LAYOUT_'+sid+'.json'),receipt)
print(json.dumps(receipt,ensure_ascii=False))
