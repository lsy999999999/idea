"""Bounded three-field inquiry over screened real fish tracks. Existing stores stay frozen."""
from __future__ import annotations

import argparse
import copy
import fcntl
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile

from fish_materials import CASE, Broker, prepare, verify, digest
from isolated_cli import invoke, parse_response
from internal_verification import EvidenceLedger, UPTAKE_TASK
from prepare import HERE, PROJECT, save
from question_state import QuestionState, PROTOCOL as QUESTION_PROTOCOL, object_hash
from run import Pilot as ExistingPilot
sys.path.insert(0, str(PROJECT / 'src'))
from learning_memory import Memory
from learning_lab import NOTE_SCHEMA


RESEARCHERS = [
    ('animal_behaviorist', '动物行为、行为生态与个体差异'),
    ('sensorimotor_biologist', '感觉生物学、运动生理与生物力学'),
    ('nonequilibrium_physicist', '非平衡动力学、状态、记忆和观测'),
]

COMMON = '''You are a peer researcher in a collaborative inquiry. Respond in Chinese, valid
JSON without Markdown fences. Use ONLY supplied scientific materials and retrieved notes.
No tools, files, network, global memory, other agents, or remembered unsupplied publications.
Scientific publications dated 2010-01-01 or later, the paper associated with these measurements,
its explanatory metadata, model/analysis code and subsequent interpretations are forbidden.
Measurements themselves are permitted. Flag possible_pretraining_familiarity; unknown is valid.
This does not erase pretrained knowledge. Never reconstruct the hidden paper from memory.
An idea can be an unresolved question, hypothesis or observation/analysis method. Do not demand
proof, implementation, novelty or experiment completion. Do not force synthesis or a distinct
view. All peers can initiate questions and change interpretations. Nobody is a fixed helper.
Keep observation, expectation, expectation_basis and conditions distinct. Published models,
measured coordinates, computed quantities and untested explanations have different status.
These tracks do not directly measure sensation, posture, forces, intention or interventions.
Use native coordinate units and frame indices; do not invent seconds, cm or body lengths.
Sources are indexed abstracts, not full papers. Explain scope across species, age and task.
All results have summary string and artifacts,evidence,claims,limitations,next_actions arrays.
Also include possible_pretraining_familiarity string. Measurements cite "measurements.json";
foundation notes cite the supplied DOI URLs. Internal report paths may be cited if supplied.
Keep response about 1600 Chinese characters; schema fields may require extra space.
'''

EVIDENCE_PROTOCOL = '''Return evidence_claims: [] or objects {id: short local ID, text,
kind: observation/inference/hypothesis, use: exploratory/research_decision,
consequence: the actual decision relying on it (empty allowed for exploratory),
basis: {source_ids: [F1/F2/F3/F4], record_ids: [R01..R13]},
depends_on: [exact earlier claim refs, stage_id:local_id]}. Backward refs within your answer
are allowed. claims is the generic runtime array; structured entries go in evidence_claims.
Register consequential factual premises even if everyone agrees. Return doubts: [] or
{claim_ref: exact earlier ref or your local ID, type: evidence_discrepancy/unproved_hypothesis,
reason: concrete mismatch, consequence: why it matters}. No compulsory objection.
An unproved conjecture is not an error or an idea rejection. Verification is scoped advice.
'''

LEARNING_REQUEST = '''Return learning_request: {needed: boolean, gap: string, why_now: string,
source_ids: [F1/F2/F3/F4], record_ids: [R01..R13], operations: [at most 3 objects]}.
Allowed operations:
{kind: window, record_id, start: inclusive frame, stop: exclusive frame, stride: positive integer};
at most 240 sampled rows per window. Or
{kind: motion/lag_correlation, record_id, start, stop, derivative_lag: 1..60,
smoothing: 1..21, score_filter: none/nonnegative, lags: up to 13 integer delays within -60..60}.
motion reports distances, displacement speeds and cosine alignment. lag_correlation reports
centered vector correlations: positive delay compares A earlier with B later; it is not a
causal test. Smoothing is a valid trailing mean without zero padding. nonnegative excludes
negative tracker codes as an analysis choice, not proof of reliable identity.
No outside URL, executable code or unavailable measurement can be requested. You can honestly
keep a gap unresolved. Ask only for material motivated by this discussion; no forced request.
'''


def load(path):
    return json.loads(Path(path).read_text())


class RecordLedger(EvidenceLedger):
    """Reuse event/provenance/queue logic, adapting only record-field admission."""
    def validate(self, stage, researcher, result):
        previous = next((e for e in self.events() if e['stage'] == stage), None)
        if previous:
            if previous['researcher'] != researcher or previous['result_hash'] != object_hash(result):
                raise ValueError('Recorded evidence result changed')
            return
        normalized = copy.deepcopy(result)
        for c in normalized.get('evidence_claims', []):
            basis = c.get('basis', {})
            if not isinstance(basis.get('record_ids'), list):
                raise ValueError('basis.record_ids must be an array')
            # Compatibility only inside the existing validator; events keep original fields.
            basis['spectrum_ids'] = basis['record_ids']
        super().validate(stage, researcher, normalized)


class FishPilot:
    def __init__(self, case=CASE, timeout=240, run_id='inquiry_001'):
        self.case = Path(case)
        self.run = self.case / 'runs' / run_id
        self.run.mkdir(parents=True, exist_ok=True)
        self.task_id = self.case.name + '/' + run_id
        self.timeout = timeout
        verify(self.case)
        self.broker = Broker(self.case)
        self.memory = Memory(self.case / 'researchers')
        self.questions = QuestionState(self.run / 'question_state', [r for r, _ in RESEARCHERS])
        self.evidence = RecordLedger(self.run / 'internal_verification', max_checks=2, batch_size=2)
        self.state_path = self.run / 'state.json'
        self.state = load(self.state_path) if self.state_path.exists() else {'protocol': 'fish-inquiry-v1', 'stages': {}}
        if self.state.get('protocol') != 'fish-inquiry-v1':
            raise ValueError('Protocol mismatch; use a new run')
        for rid, domain in RESEARCHERS:
            original = PROJECT / 'learning_lab/researchers' / rid / 'identity.json'
            target = self.memory.root / rid / 'identity.json'
            if original.exists() and not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(original, target)
            self.memory.identity(rid, domain)
        setup = self.run / 'FROZEN_SETUP.json'
        if not setup.exists():
            save(setup, {'model_requested': 'gpt-6-luna', 'rounds': 2,
                 'initial_window_rule': 'R01/R07/R13, frames [1000,1160), stride 4; fixed before generation, not selected for an anomaly',
                 'initial_motion_analysis': False, 'forced_target_question': False,
                 'source_cutoff': '2010-01-01 exclusive', 'source_access': '4 actual indexed abstracts',
                 'memory_screening': 'Existing identities retained; original notes preserved in original stores but not supplied: no complete pre-2010 dependency audit. New branch notes persist across all stages.',
                 'code_sha256': {n: digest(HERE / n) for n in ('fish_pilot.py', 'fish_materials.py', 'isolated_cli.py', 'question_state.py', 'internal_verification.py')},
                 'allowed_sha256': load(self.case / 'controller_only/allowed_hashes.json')})
            for n in load(setup)['code_sha256']:
                dest = self.run / 'protocol_snapshot' / n
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(HERE / n, dest)
        for name, expected in load(setup)['code_sha256'].items():
            if digest(HERE / name) != expected:
                raise ValueError('Frozen controller changed; choose a new run ID')

    def packet(self, sid, rid):
        path = self.run / 'memory_retrieval' / (sid + '.json')
        if not path.exists():
            save(path, self.memory.retrieve(rid, 'fish motion perception physiology interaction memory 游动 感知 时间 条件 解释'))
        return load(path)

    def validate(self, sid, role, result, context, notes, initial):
        if not isinstance(result, dict) or not isinstance(result.get('summary'), str):
            raise ValueError('A result object with summary is required')
        for key in ('artifacts', 'evidence', 'claims', 'limitations', 'next_actions'):
            if not isinstance(result.get(key), list):
                raise ValueError('Missing runtime array ' + key)
        if role in self.questions.researchers:
            self.evidence.validate(sid, role, result)
            for c in result.get('evidence_claims', []):
                self.broker.request(c['basis'])
            self.questions.validate(sid, role, result, context.get('question_state'), initial)
        if role == 'internal_evidence_verifier':
            self.evidence.validate_findings(result, context['targets'], context['evidence_catalog'])
        if 'verification_report' in context:
            replies = result.get('verification_responses', [])
            refs = [r.get('claim_ref') for r in replies]
            needed = {f['claim_ref'] for f in context['verification_report']['findings']}
            if len(refs) != len(set(refs)) or not needed <= set(refs) or any(r not in self.evidence.claims() for r in refs):
                raise ValueError('Respond to all supplied findings using exact claim refs')
            for r in replies:
                if r.get('stance') not in {'accept', 'rebut', 'unresolved'} or not r.get('reason') or not r.get('changed_understanding') or r.get('question_effect') not in {'retain', 'revise', 'unresolved'}:
                    raise ValueError('Each response needs a reason, scoped change and question_effect')
            updates = {n['key']: n for n in result.get('memory_notes', [])}
            report = context['verification_report_path']
            for note in context['affected_notes']:
                n = updates.get(note['key'], {})
                if n.get('kind') != 'correction' or report not in n.get('sources', []) or not n.get('revision_reason'):
                    raise ValueError('Affected notes need a sourced same-key correction/dispute version')
            if not any(n.get('kind') == 'correction' and report in n.get('sources', []) for n in updates.values()):
                raise ValueError('Save your own response as a sourced correction/dispute note')
        allowed_sources = {'measurements.json'} | {s['doi'] for s in self.broker.sources.values()}
        report_sources = {r['report_path'] for r in self.evidence.reports()}
        allowed_sources |= report_sources
        if notes and not result.get('memory_notes'):
            raise ValueError('At least one actual learning note is required')
        for n in result.get('memory_notes', []):
            if any(s not in allowed_sources for s in n.get('sources', [])):
                raise ValueError('Note cites an unavailable or forbidden source')
            old = self.memory.index(role)['notes'].get(n['key'])
            if old:
                previous = load(old['path'])
                if not n.get('revision_reason') or not (set(previous['sources']) & report_sources) <= set(n['sources']):
                    raise ValueError('A revision needs its reason and previous correction sources')
        if notes:
            with tempfile.TemporaryDirectory() as temp:
                p = Path(temp) / 'result.json'
                save(p, result)
                Memory(Path(temp) / 'memory').commit(role, self.task_id, sid, p)
        if 'learning_request' in result and (not isinstance(result['learning_request'], dict) or not isinstance(result['learning_request'].get('needed'), bool)):
            raise ValueError('learning_request.needed must be a boolean')
        if role == 'discussion_recorder' and not isinstance(result.get('ideas'), list):
            raise ValueError('Recorder must return ideas array')
        if role == 'historical_final_evaluator':
            checks = result.get('checks', [])
            if len(checks) != len(context['ideas']) or {c.get('idea_id') for c in checks} != {i['id'] for i in context['ideas']}:
                raise ValueError('Final check must cover every frozen idea exactly once')
            for c in checks:
                for key, allowed in [('prior_work', {'close_direction_found', 'no_close_work_found', 'unclear'}),
                                     ('math', {'no_obvious_error', 'obvious_error', 'unclear'})]:
                    if not isinstance(c.get(key), dict) or c[key].get('verdict') not in allowed or not c[key].get('reason'):
                        raise ValueError('Final check needs separate supported verdicts')
                if c.get('novelty', {}).get('coverage') not in {'covered', 'partial', 'unclear'}:
                    raise ValueError('Final novelty coverage required')

    def call(self, sid, role, task, context, notes=False):
        researcher = role in self.questions.researchers
        initial = sid.startswith('01_initial_') and researcher
        context = {**context, '_stage': sid}
        if researcher:
            context['researcher'] = role
            context['memory'] = self.packet(sid, role)
            context['evidence_state'] = self.evidence.history_packet(sid, independent=initial)
            task += '\n' + EVIDENCE_PROTOCOL
            if not initial:
                context['question_state'] = self.questions.packet(sid, role)
                task += '\n' + QUESTION_PROTOCOL
        if notes:
            task += '\n' + NOTE_SCHEMA + '\nRetain previous internal-correction report sources when revising notes.'
        prompt = COMMON + '\nROLE: ' + role + '\n' + task + '\nINPUTS:\n' + json.dumps(context, ensure_ascii=False)
        fingerprint = hashlib.sha256(prompt.encode()).hexdigest()
        path = self.run / 'stages' / sid / 'result.json'
        if sid in self.state['stages']:
            record = self.state['stages'][sid]
            if record['input_sha256'] != fingerprint or record['output_sha256'] != digest(path):
                raise ValueError('Frozen stage input/output changed')
            return load(path)
        root = path.parent
        root.mkdir(parents=True, exist_ok=True)
        number = max([int(p.name.split('-')[-1]) for p in root.glob('attempt-*')], default=0)+1
        last = root / f'attempt-{number-1:03d}'
        print(json.dumps({'stage': sid, 'status': 'started', 'requested_model': 'gpt-6-luna'}), flush=True)
        if ((last / 'execution_audit.json').exists() and load(last / 'execution_audit.json')['returncode'] == 0
                and load(last / 'execution_audit.json')['tool_events'] == 0
                and ((last / 'prompt.txt').read_text() == prompt or (last / 'prompt.txt').read_text().startswith(prompt+'\nSCHEMA REPAIR ONLY.'))):
            raw = parse_response((last / 'final.txt').read_text())
        else:
            raw = invoke(prompt, root / f'attempt-{number:03d}', self.timeout)
            number += 1
        result = ExistingPilot.admit_bookkeeping(raw, researcher, context.get('targets') if role == 'internal_evidence_verifier' else None)
        try:
            self.validate(sid, role, result, context, notes, initial)
        except ValueError as error:
            repair = prompt + '\nSCHEMA REPAIR ONLY. Preserve scientific content. Fix only field layout, exact refs, allowed source strings or required metadata. Do not add claims or interpretations. Error: ' + str(error) + '\nUNADMITTED ANSWER:\n' + json.dumps(result, ensure_ascii=False)
            raw = invoke(repair, root / f'attempt-{number:03d}', self.timeout)
            result = ExistingPilot.admit_bookkeeping(raw, researcher, context.get('targets') if role == 'internal_evidence_verifier' else None)
            self.validate(sid, role, result, context, notes, initial)
        save(path, result)
        if notes:
            self.memory.commit(role, self.task_id, sid, path)
        if researcher:
            self.questions.accept(sid, role, result, path, context.get('question_state'), initial)
            self.evidence.observe(sid, role, result, path)
        self.state['stages'][sid] = {'input_sha256': fingerprint, 'output_sha256': digest(path)}
        save(self.state_path, self.state)
        print(json.dumps({'stage': sid, 'status': 'complete'}), flush=True)
        return result

    def verification(self, boundary):
        batch = self.evidence.select(boundary)
        if not batch['targets']:
            return []
        packet_path = self.run / 'internal_verification/packets' / (boundary+'.json')
        if not packet_path.exists():
            claims = self.evidence.claims()
            needed = {t['ref']: t for t in batch['targets']}
            pending = list(needed.values())
            while pending:
                for dep in pending.pop()['depends_on']:
                    if dep not in needed:
                        needed[dep] = claims[dep]
                        pending.append(claims[dep])
            records = sorted({r for c in needed.values() for r in c['basis']['record_ids']})
            sources = sorted({r for c in needed.values() for r in c['basis']['source_ids']})
            catalog = {f'source:{s}': self.broker.sources[s] for s in sources}
            for rid in records:
                catalog['motion:'+rid] = self.broker.operation({'kind': 'motion', 'record_id': rid})
                catalog['window:'+rid] = self.broker.operation({'kind': 'window', 'record_id': rid, 'start': 1000, 'stop': 1120, 'stride': 4})
            # Include the EXACT material any author actually saw, not just a final summary.
            for p in sorted((self.run / 'broker').glob('*.json')):
                catalog['broker:'+p.stem] = load(p)
            stages = {c['stage'] for c in needed.values()}
            original = [{'stage': e['stage'], 'result': load(e['source_result']), 'sha256': e['source_sha256']}
                        for e in self.evidence.events() if e['stage'] in stages]
            save(packet_path, {'targets': batch['targets'], 'triggers': batch['triggers'], 'evidence_catalog': catalog,
                               'original_arguments': original, 'measurement_metadata': self.broker.catalog})
        packet = load(packet_path)
        sid = boundary+'_verify'
        report = self.call(sid, 'internal_evidence_verifier', '''Check only target statements using the supplied original evidence and computations. Return findings [{claim_ref,status:supported/needs_correction/undetermined,reason,evidence_refs:exact evidence_catalog keys,corrected_claim:scoped text or null}]. A correlation or time lag does not itself identify influence or physiological mechanism. Raw and smoothed derivatives differ. Missing evidence for a conjecture is not a refutation. No novelty or idea acceptance verdict. claims may be [].''', packet)
        report_path = self.run / 'stages' / sid / 'result.json'
        self.evidence.record_report(boundary, report, report_path)
        affected_path = self.run / 'internal_verification/affected' / (boundary+'.json')
        if not affected_path.exists():
            save(affected_path, self.evidence.relevant([f['claim_ref'] for f in report['findings']]))
        affected = load(affected_path)
        responses = []
        for i, (rid, _) in enumerate(RESEARCHERS):
            sid = boundary+f'_discuss_{i}'
            inputs = self.run / 'internal_verification/uptake_inputs' / (sid+'.json')
            if not inputs.exists():
                stages = {c['stage'] for c in affected if c['author'] == rid}
                keys = {load(p)['key'] for p in (self.memory.root/rid/'notes').glob('*/v*.json')
                        if load(p)['source_task'] == self.task_id and load(p)['source_stage'] in stages}
                save(inputs, {'affected_notes': [load(v['path']) for k, v in self.memory.index(rid)['notes'].items() if k in keys]})
            result = self.call(sid, rid, UPTAKE_TASK, {'verification_report': report,
                     'verification_report_path': str(report_path.resolve()), 'affected_claims': affected,
                     'earlier_peer_responses': responses, **load(inputs)}, notes=True)
            responses.append({'researcher': rid, 'result': result})
        save(self.run / 'internal_verification/discussion' / (boundary+'.json'), responses)
        return responses

    def execute(self):
        initial_context = self.run / 'initial_materials.json'
        if not initial_context.exists():
            save(initial_context, {'measurement_metadata': self.broker.catalog,
                 'sampled_windows': self.broker.request({'operations': [
                     {'kind': 'window', 'record_id': r, 'start': 1000, 'stop': 1160, 'stride': 4}
                     for r in ('R01', 'R07', 'R13')]}),
                 'source_catalog': [{k: s[k] for k in ('id', 'title', 'date', 'doi', 'access')} for s in self.broker.sources.values()]})
        initial, history, corrections = [], [], []
        foundations = [('F2', 'F1'), ('F1', 'F3'), ('F2', 'F3')]
        for i, (rid, domain) in enumerate(RESEARCHERS):
            result = self.call(f'01_initial_{i}', rid, '''Study your actual foundation excerpts, explain one concrete concept with a small example and limits, then independently inspect the measurements. Return observation,expectation,expectation_basis,conditions,initial_question,question_to_peers,worked_example, memory_notes (1-2 useful notes). Do not invent an anomaly or infer behavior from a model alone. You can honestly say the available evidence does not support a specific explanation yet.''',
                {**load(initial_context), 'domain': domain, 'foundations': [self.broker.sources[f] for f in foundations[i]]}, notes=True)
            initial.append({'researcher': rid, 'result': result})
        for round_id in (1, 2):
            exchanges = []
            for i, (rid, _) in enumerate(RESEARCHERS):
                result = self.call(f'r{round_id}_exchange_{i}', rid, '''Respond to specific peer interpretations and pursue any line you now consider useful. Return response_to_peers, noticed_difference, changed_understanding, shared_object, branches (preserve unfinished/abandoned ideas with reasons). Quote a concrete peer statement if it changes your view; no imaginary breakthrough. The shared question may stay unchanged. '''+LEARNING_REQUEST,
                    {'initial': initial, 'previous_rounds': history, 'internal_discussions': corrections, 'earlier_exchanges_this_round': exchanges})
                exchanges.append({'researcher': rid, 'result': result})
            learned = []
            for i, (rid, _) in enumerate(RESEARCHERS):
                request = exchanges[i]['result'].get('learning_request', {'needed': False})
                if request['needed']:
                    sid = f'r{round_id}_learn_{i}'
                    path = self.run / 'broker' / (sid+'.json')
                    if not path.exists():
                        try:
                            reply = self.broker.request(request)
                        except ValueError as error:
                            reply = {'request': request, 'unavailable': str(error), 'computed': [], 'sources': []}
                        save(path, reply)
                    result = self.call(sid, rid, '''Study the material you actually requested, including any unavailable gaps. Return learning_change, worked_example, remaining_gap and memory_notes. Distinguish the controller's executed computations from your interpretations. If evidence cannot distinguish explanations, retain that uncertainty; do not describe a proof or a new measurement that did not occur.''',
                        {'your_request': request, 'broker_reply': load(path), 'exchanges': exchanges}, notes=True)
                    learned.append({'researcher': rid, 'result': result})
            checked = self.verification(f'r{round_id}_evidence')
            corrections.extend(checked)
            returned = []
            for i, (rid, _) in enumerate(RESEARCHERS):
                result = self.call(f'r{round_id}_return_{i}', rid, '''Return to common discussion using what everyone actually learned. Respond to concrete peer statements and develop or revise a question, explanation or method. Return shared_object, changed_because, branches (including uncertain and abandoned branches), memory_notes. Describe exactly what changed and why; unchanged is valid. Do not force an interdisciplinary synthesis or convert a limitation into a discovery claim.''',
                    {'initial': initial, 'prior_rounds': history, 'exchanges': exchanges, 'learning': learned,
                     'internal_discussions': corrections, 'earlier_returns': returned}, notes=True)
                returned.append({'researcher': rid, 'result': result})
            history.append({'round': round_id, 'exchanges': exchanges, 'learning': learned, 'returned': returned})
        rid = RESEARCHERS[-1][0]
        fresh = self.call('04_fresh_continuation', rid, '''Fresh session: use retrieved current notes and explicit question state, without the full dialogue. Return memory_use [{key,version,source_task,scope_check}], continuation_question, a worked_example, and remaining_gap. Continue an actual saved line; distinguish stored understanding from a new proposal.''', {'measurement_metadata': self.broker.catalog})
        ideas = self.call('05_candidates', 'discussion_recorder', '''Record 0-4 ideas actually present in the discussion. Do not invent stronger hypotheses or combine fields just for appearance. Return ideas [{id,title,idea,motivation,emergence:stage refs and actual changes,supporting_claim_refs:exact refs}], question_trajectory, preserved_branches. Preserve a question even when its original rationale was corrected. An unfinished idea is valid. State which changes are wording, which reinterpret evidence, and which actually change the question, with quotations.''',
            {'initial': initial, 'rounds': history, 'internal_discussions': corrections, 'fresh_continuation': fresh,
             **self.questions.history_packet('05_candidates'), 'evidence_history': self.evidence.history_packet('05_candidates')})
        save(self.run / 'ideas.json', ideas)
        freeze = self.run / 'GENERATION_FREEZE.json'
        if not freeze.exists():
            paths = [self.run / 'ideas.json']
            for sub in ('stages', 'broker', 'question_state', 'internal_verification', 'memory_retrieval'):
                paths.extend(p for p in (self.run/sub).rglob('*.json') if '06_final_check' not in str(p))
            save(freeze, {'files': {str(p.resolve()): digest(p) for p in paths}, 'external_feedback_used_for_generation': False})
        memory_before = {str(p): digest(p) for p in self.memory.root.rglob('*.json')}
        checked = self.call('06_final_check', 'historical_final_evaluator', '''Independent FINAL check; outputs are frozen and no feedback returns to researchers. Two duties only: compare core ideas to supplied eligible prior sources, and flag obvious math/logical errors. Return checks [{idea_id,prior_work:{verdict:close_direction_found/no_close_work_found/unclear,reason,sources},math:{verdict:no_obvious_error/obvious_error/unclear,reason,errors},novelty:{core_claims,coverage:covered/partial/unclear,reason}}]. Assess each original claim faithfully. Direction overlap alone is not complete coverage. This closed 4-abstract pre-2010 corpus is not a broad literature search; absent a direct positive coverage witness, novelty must remain unclear. No hidden origin paper or later works may be retrieved. Missing proof, intervention, experiments or calibration is not itself a mathematical error; overstating an observed correlation as identified causation can be an inference error. Keep every original candidate.''',
            {'ideas': ideas['ideas'], 'eligible_sources': list(self.broker.sources.values()),
             'discussion': {'initial': initial, 'rounds': history, 'corrections': corrections, 'fresh': fresh},
             'actual_broker_evidence': {p.stem: load(p) for p in sorted((self.run/'broker').glob('*.json'))},
             'measurement_metadata': self.broker.catalog, 'evaluation_scope': 'bounded pre-2010 corpus; incomplete originality assessment'})
        save(self.run / 'check_report.json', checked)
        if memory_before != {str(p): digest(p) for p in self.memory.root.rglob('*.json')}:
            raise ValueError('Final evaluator modified research memory')
        for p, expected in load(freeze)['files'].items():
            if digest(p) != expected:
                raise ValueError('Frozen generation changed')
        save(self.run / 'EVALUATION_ISOLATION.json', {'memory_unchanged': True, 'researcher_calls_after_evaluation': 0,
             'generation_freeze_sha256': digest(freeze), 'scope': 'closed historical adapter, not the general broad-search claim-centric evaluator'})
        self.state['status'] = 'complete'
        save(self.state_path, self.state)
        self.audit()

    def audit(self):
        verify(self.case)
        protected = load(self.case / 'controller_only/protected_hashes.json')
        changed = [p for p, expected in protected.items() if digest(p) != expected]
        events = [load(p) for p in (self.run/'stages').glob('*/attempt-*/execution_audit.json')]
        reports = self.evidence.reports()
        source_tokens = ('10.1098/rspb.2017.0224', 'dryad.f0g32', 'Signatures of optimal control',
                         '20150901T', 'FishHistograms', 'scaleD=35/1000')
        exposure = []
        for p in (self.run/'stages').glob('*/attempt-*/prompt.txt'):
            if any(t in p.read_text() for t in source_tokens):
                exposure.append(str(p))
        result = {'status': 'pass' if not changed and not exposure and not sum(e['tool_events'] for e in events) else 'fail',
                  'protected_original_files': len(protected), 'changed_original_files': changed,
                  'forbidden_source_token_hits': exposure, 'tool_events': sum(e['tool_events'] for e in events),
                  'requested_models': sorted({e['requested_model'] for e in events}), 'raw_attempts': len(events),
                  'logical_stages': len(self.state['stages']), 'internal_verification_batches': len(reports),
                  'source_date_hash_checks_passed': True, 'pretraining_exclusion_claimed': False,
                  'original_memory_implementation_changed': False}
        save(self.run/'AUDIT.json', result)
        if result['status'] != 'pass':
            raise ValueError('Preservation or supplied-input audit failed')
        print(json.dumps(result), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--timeout', type=int, default=240)
    parser.add_argument('--run-id', default='inquiry_001')
    args = parser.parse_args()
    if not args.run_id.replace('_', '').isalnum():
        parser.error('Use a safe run ID')
    prepare()
    with (CASE/'.run.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        FishPilot(timeout=args.timeout, run_id=args.run_id).execute()
