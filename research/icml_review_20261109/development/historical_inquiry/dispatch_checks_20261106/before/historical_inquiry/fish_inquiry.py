"""Collaborative inquiry with task-screened online learning and researcher-led analysis."""
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

from fish_materials import CASE, prepare, verify, digest
from inquiry_services import InquiryBroker, NoteGate
from analysis_executor import PLAN_PROTOCOL
from note_dependencies import prepare_dependencies
from final_evaluation import evaluate_final
from isolated_cli import invoke, parse_response
from internal_verification import EvidenceLedger, UPTAKE_TASK
from prepare import HERE, PROJECT, save
from question_state import QuestionState, PROTOCOL as QUESTION_PROTOCOL, object_hash
from hypothesis_development import HypothesisState, PROTOCOL as HYPOTHESIS_PROTOCOL
from run import Pilot as ExistingPilot
sys.path.insert(0, str(PROJECT / 'src'))
from learning_memory import Memory
from learning_lab import NOTE_SCHEMA
from idea_check import validate_checks, validate_ideas


RESEARCHERS = [
    ('animal_behaviorist', '动物行为、行为生态与个体差异'),
    ('sensorimotor_biologist', '感觉生物学、运动生理与生物力学'),
    ('nonequilibrium_physicist', '非平衡动力学、状态、记忆和观测'),
]

COMMON = """You are a peer researcher. Respond in Chinese, valid JSON. Use supplied evidence
and screened notes; make knowledge and analysis requests through the controller. Work within
the task's configured knowledge date and source exclusions. Raw measurements and screened
measurement context are permitted. Keep observation, expectation, expectation_basis and
conditions distinct. Propose and revise observation definitions, comparison conditions and
explanations. Separate missing external facts, definitions you can choose, and interface gaps.
A missing fact limits the relevant inference; pursue other useful questions. Ideas may be
unfinished. All results include a summary string, artifacts/evidence/claims/limitations/next_actions
arrays and possible_pretraining_familiarity string. Cite actual supplied sources and distinguish
reading, explaining and using knowledge. Keep useful concepts/examples in memory, revise
same keys when understanding changes. No compulsory tool use or manufactured disagreement.
"""

EVIDENCE_PROTOCOL = """Return evidence_claims: [] or {id,text,
kind:observation/inference/hypothesis,use:exploratory/research_decision,consequence,
basis:{source_ids:[actual supplied source IDs],record_ids:[actual record IDs]},
depends_on:[exact earlier stage:claim refs]}. Include decisions to stop or deprioritize data
analysis with their actual premises. Return doubts: [] or {claim_ref,
type:evidence_discrepancy/unproved_hypothesis,reason,consequence}. An unfinished hypothesis
is not an error. Record a specific inference and its consequence, not repeated generic limits.
"""

LEARNING_REQUEST = """Return learning_request:{needed:boolean,gap,why_now,
queries:[free text queries for any relevant foundations/models/examples/methods/material types],
urls:[optional identifiers or URLs to find and verify],source_ids:[],record_ids:[],operations:[]}.
Knowledge requests automatically trigger online search and reading, not human approval.
Only actually read, date-verified content is returned. You may ask again if a search fails.
""" + PLAN_PROTOCOL + """
Return exploration:{missing_external_facts:[],unselected_definitions:[],interface_gaps:[],
next_action,stalled_reason,understanding_changed:boolean}. When progress stalls, choose
conceptual development of an assumption or its consequences, an alternative observation/definition,
request useful knowledge/computation, or explicitly park
the branch with a reason. No forced tool request or completed formula/experiment is required.
"""


def load(path):
    return json.loads(Path(path).read_text())


def admit_reference_layout(result, sid, broker):
    """Resolve only exact reference notation; never change scientific text or choices."""
    result = copy.deepcopy(result)
    claims = copy.deepcopy(result.get('evidence_claims', []))
    if not isinstance(claims, list):
        return result
    data_sources = {'measurements.json', broker.catalog['measurement_context']['data_source']['doi']}
    earlier, changes = set(), []
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        basis = claim.get('basis', {})
        if isinstance(basis, dict) and isinstance(basis.get('source_ids'), list):
            data = [s for s in basis['source_ids'] if isinstance(s, str) and s in data_sources]
            if data:
                before = copy.deepcopy(basis)
                basis['source_ids'] = [s for s in basis['source_ids'] if s not in data]
                basis['measurement_sources'] = list(dict.fromkeys(basis.get('measurement_sources', []) + data))
                changes.append({'claim_id': claim.get('id'), 'field': 'basis', 'before': before, 'after': copy.deepcopy(basis)})
        dependencies = claim.get('depends_on')
        if isinstance(dependencies, list):
            fixed = [sid + ':' + ref if isinstance(ref, str) and ref in earlier else ref for ref in dependencies]
            if fixed != dependencies:
                changes.append({'claim_id': claim.get('id'), 'field': 'depends_on', 'before': dependencies, 'after': fixed})
                claim['depends_on'] = fixed
        if isinstance(claim.get('id'), str):
            earlier.add(claim['id'])
    if changes:
        result['evidence_claims'] = claims
        result['controller_reference_admission'] = {'changes': changes, 'scientific_content_changed': False}
    return result


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

    def select(self, boundary):
        path = self.root / 'batches' / (boundary + '.json')
        if path.exists():
            return load(path)
        claims = self.claims()
        checked = {f['claim_ref'] for r in self.reports() for f in r['findings']}
        checked_arguments = {(claims[r]['text'].strip(), claims[r]['consequence'].strip()) for r in checked}
        candidates, deferred = {}, []
        for event in self.events():
            for doubt in event['doubts']:
                if doubt['type'] == 'unproved_hypothesis':
                    deferred.append({**doubt, 'disposition': 'not_an_error_or_gate'})
                elif doubt['claim_ref'] not in checked:
                    candidates.setdefault(doubt['claim_ref'], []).append(doubt)
        for ref, claim in claims.items():
            if claim['kind'] != 'hypothesis' and claim['use'] == 'research_decision' and ref not in checked:
                argument = (claim['text'].strip(), claim['consequence'].strip())
                if argument not in checked_arguments:
                    candidates.setdefault(ref, []).append({'type': 'consequential_premise', 'reason': claim['consequence']})
        def priority(ref):
            consequence = claims[ref]['consequence'].lower()
            stopping = any(word in consequence for word in ('stop', 'abandon', 'no value', 'unnecessary', '暂停', '停止', '放弃', '没有价值', '无需', '不能继续', '不再'))
            explicit = any(t['type'] == 'evidence_discrepancy' for t in candidates[ref])
            return (not explicit, not stopping)
        ranked, duplicates, arguments = [], [], set()
        for ref in sorted(candidates, key=priority):
            argument = (claims[ref]['text'].strip(), claims[ref]['consequence'].strip())
            if argument in arguments:
                duplicates.append(ref)
            else:
                ranked.append(ref)
                arguments.add(argument)
        limit = self.batch_size if len(self.reports()) < self.max_checks else 0
        selected = ranked[:limit]
        value = {'boundary': boundary, 'targets': [claims[r] for r in selected],
                 'triggers': {r: candidates[r] for r in selected}, 'pending_refs': ranked[len(selected):],
                 'duplicate_argument_refs': duplicates, 'deferred': deferred,
                 'budget_exhausted': bool(ranked and not limit)}
        save(path, value)
        return value


class InquiryPilot:
    def __init__(self, case=CASE, timeout=240, run_id='inquiry_v2', config=None, fetch=None):
        if not run_id or not run_id.replace('_', '').isalnum():
            raise ValueError('Use a safe run ID')
        self.case = Path(case)
        self.run = self.case / 'runs' / run_id
        self.run.mkdir(parents=True, exist_ok=True)
        preserved = self.run / 'PRESERVED_RECORDS.json'
        if not preserved.exists():
            paths = [p for folder in (self.case / 'runs', self.case / 'researchers', PROJECT / 'learning_lab/researchers')
                     for p in folder.rglob('*') if p.is_file() and self.run not in p.parents]
            save(preserved, {str(p.resolve()): digest(p) for p in paths})
        self.task_id = self.case.name + '/' + run_id
        self.timeout = timeout
        verify(self.case)
        self.config = config or load(HERE / 'configs/fish_v2.json')
        for key in ('max_rounds', 'max_request_hops', 'retrieval_results_per_query'):
            if type(self.config.get(key)) is not int or self.config[key] < 1:
                raise ValueError('Task config needs positive integer ' + key)
        if self.config.get('raw_measurement_exception') is not True:
            raise ValueError('This fish adapter requires the explicit raw measurement exception')
        self.broker = InquiryBroker(self.case, self.run / 'services', self.config, self.plan_analysis, fetch)
        self.memory = Memory(self.case / 'researchers_v2')
        self.note_gate = NoteGate(self.broker, [self.memory.root, self.case / 'researchers', PROJECT / 'learning_lab/researchers'])
        self.questions = QuestionState(self.run / 'question_state', [r for r, _ in RESEARCHERS])
        self.hypotheses = HypothesisState(self.run / 'hypothesis_state', [r for r, _ in RESEARCHERS])
        self.evidence = RecordLedger(self.run / 'internal_verification', max_checks=self.config.get('max_internal_batches', 2), batch_size=2)
        self.state_path = self.run / 'state.json'
        self.state = load(self.state_path) if self.state_path.exists() else {'protocol': 'open-inquiry-v2', 'stages': {}}
        if self.state.get('protocol') != 'open-inquiry-v2':
            raise ValueError('Protocol mismatch; use a new run')
        for rid, domain in RESEARCHERS:
            original = PROJECT / 'learning_lab/researchers' / rid / 'identity.json'
            target = self.memory.root / rid / 'identity.json'
            if original.exists() and not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(original, target)
            self.memory.identity(rid, domain)
        setup = self.run / 'FROZEN_SETUP.json'
        code_sources = {name: HERE / name for name in (
            'fish_inquiry.py', 'inquiry_services.py', 'knowledge_broker.py', 'analysis_executor.py',
            'note_dependencies.py', 'final_evaluation.py', 'fish_materials.py', 'isolated_cli.py',
            'question_state.py', 'hypothesis_development.py', 'internal_verification.py', 'prepare.py', 'run.py')}
        code_sources.update({'shared/' + name: PROJECT / 'src' / name for name in (
            'idea_check.py', 'novelty_contract.py', 'novelty_scope.py', 'learning_memory.py',
            'learning_lab.py', 'discover.py', 'runtime.py')})
        if not setup.exists():
            save(setup, {'model_requested': 'gpt-6-luna', 'max_rounds': self.config['max_rounds'], 'task_config': self.config,
                 'initial_window_rule': 'R01/R07/R13, frames [1000,1160), stride 4; fixed before generation, not selected for an anomaly',
                 'initial_motion_analysis': False, 'forced_target_question': False,
                 'source_cutoff': self.config['knowledge_before_exclusive'], 'source_access': 'Task-filtered online retrieval and reading on request',
                 'memory_screening': 'Existing identities and stores retained; current notes admitted only after source/date/dependency/content screening. Read/explained/used remain separate.',
                 'code_sha256': {name: digest(path) for name, path in code_sources.items()},
                 'allowed_sha256': load(self.case / 'controller_only/allowed_hashes.json')})
            for n in load(setup)['code_sha256']:
                dest = self.run / 'protocol_snapshot' / n
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(code_sources[n], dest)
        if load(setup)['task_config'] != self.config:
            raise ValueError('Task config changed; choose a new run ID')
        if set(load(setup)['code_sha256']) != set(code_sources):
            raise ValueError('Frozen dependency set changed; choose a new run ID')
        for name, expected in load(setup)['code_sha256'].items():
            if digest(code_sources[name]) != expected:
                raise ValueError('Frozen controller changed; choose a new run ID')

    def packet(self, sid, rid):
        path = self.run / 'memory_retrieval' / (sid + '.json')
        if not path.exists():
            self.note_gate.retrieve(rid, 'fish motion perception physiology interaction memory 游动 感知 时间 条件 解释', path)
        return load(path)

    def validate(self, sid, role, result, context, notes, initial):
        if not isinstance(result, dict) or not isinstance(result.get('summary'), str):
            raise ValueError('A result object with summary is required')
        for key in ('artifacts', 'evidence', 'claims', 'limitations', 'next_actions'):
            if not isinstance(result.get(key), list):
                raise ValueError('Missing runtime array ' + key)
        if role == 'historical_final_evaluator':
            if result.get('memory_notes'):
                raise ValueError('Final evaluation cannot update research memory')
            validate_checks(result, context['ideas'], require_claims=True)
            return
        if self.broker.policy.forbidden(result):
            raise ValueError('Output contains excluded source identity/content')
        if role in self.questions.researchers:
            visible = json.dumps(context, ensure_ascii=False)
            supplied_ids = {key for key, source in self.broker.sources.items() if source['doi'] in visible or ('"' + key + '"') in visible}
            self.evidence.validate(sid, role, result)
            for c in result.get('evidence_claims', []):
                self.broker.check_basis(c['basis'])
                if any(key not in supplied_ids for key in c['basis']['source_ids']):
                    raise ValueError('Evidence cites material not supplied to this researcher')
            self.questions.validate(sid, role, result, context.get('question_state'), initial)
            self.hypotheses.validate(sid, role, result, context.get('hypothesis_state'))
            exploration = result.get('exploration')
            if not isinstance(exploration, dict) or not isinstance(exploration.get('understanding_changed'), bool):
                raise ValueError('Exploration needs an explicit understanding_changed boolean')
            for key in ('missing_external_facts', 'unselected_definitions', 'interface_gaps'):
                if not isinstance(exploration.get(key), list):
                    raise ValueError('Exploration needs ' + key + ' array')
            if not exploration.get('next_action') and not exploration.get('stalled_reason'):
                raise ValueError('Name a next action or the actual stagnation reason')
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
            supported_unchanged = all(f['status'] == 'supported' for f in context['verification_report']['findings']) and all(r['stance'] == 'accept' and r['question_effect'] == 'retain' for r in replies)
            for note in context['affected_notes']:
                if supported_unchanged and note['key'] not in updates:
                    continue
                n = updates.get(note['key'], {})
                if n.get('kind') != 'correction' or report not in n.get('sources', []) or not n.get('revision_reason'):
                    raise ValueError('Affected notes need a sourced same-key correction/dispute version')
            # Unchanged supported premises need no duplicate limitation note.
        allowed_sources = {'measurements.json', self.broker.catalog['measurement_context']['data_source']['doi']} | {s['doi'] for s in self.broker.sources.values()}
        report_sources = {r['report_path'] for r in self.evidence.reports()}
        inherited_notes = {}
        if role in self.questions.researchers:
            allowed_sources &= {'measurements.json', self.broker.catalog['measurement_context']['data_source']['doi']} | {self.broker.sources[k]['doi'] for k in supplied_ids}
        allowed_sources |= report_sources
        for old in self.packet(sid, role)['retrieved'] if role in self.questions.researchers else []:
            allowed_sources.update(old['note']['sources'])
            inherited_notes[old['note']['key']] = old['note']
            report_sources.update(source for source in old['note']['sources']
                                  if source not in self.broker.sources
                                  and source not in {s['doi'] for s in self.broker.sources.values()}
                                  and source not in {'measurements.json', self.broker.catalog['measurement_context']['data_source']['doi']})

        for n in result.get('memory_notes', []):
            if any(s not in allowed_sources for s in n.get('sources', [])):
                raise ValueError('Note cites an unavailable or forbidden source')
            old = self.memory.index(role)['notes'].get(n['key'])
            previous = load(old['path']) if old else inherited_notes.get(n['key'])
            if previous:
                if not n.get('revision_reason') or not (set(previous['sources']) & report_sources) <= set(n['sources']):
                    raise ValueError('A revision needs its reason and previous correction sources')
        if result.get('memory_notes'):
            # Resolve inherited reports and the entire scientific closure BEFORE persistence.
            prepare_dependencies(self, result, context)
            with tempfile.TemporaryDirectory() as temp:
                p = Path(temp) / 'result.json'
                save(p, result)
                Memory(Path(temp) / 'memory').commit(role, self.task_id, sid, p)
        if 'learning_request' in result:
            req = result['learning_request']
            if not isinstance(req, dict) or not isinstance(req.get('needed'), bool):
                raise ValueError('learning_request.needed must be a boolean')
            for key in ('queries', 'urls', 'source_ids', 'record_ids', 'operations'):
                if not isinstance(req.get(key, []), list):
                    raise ValueError('Request ' + key + ' must be an array')
            if any(not isinstance(op, dict) for op in req.get('operations', [])):
                raise ValueError('Each computation request must be an object')
        if role == 'discussion_recorder':
            if not isinstance(result.get('ideas'), list):
                raise ValueError('Recorder must return ideas array')
            if result['ideas']:
                validate_ideas(result)
            if any('evaluation_context' in idea for idea in result['ideas']):
                raise ValueError('Generation cannot declare evaluation exposure or dates')
            expected = [c['ref'] for c in context.get('current_hypotheses', [])]
            if expected:
                preserved = result.get('preserved_branches')
                if not isinstance(preserved, list) or any(not isinstance(b, dict) for b in preserved):
                    raise ValueError('Recorder must account for all hypothesis branches')
                refs = [b.get('ref') for b in preserved]
                if len(refs) != len(expected) or any(refs.count(ref) != 1 for ref in expected):
                    raise ValueError('Recorder must preserve each exact hypothesis ref once')
                if any(not isinstance(b.get('reason'), str) or not b['reason'].strip() for b in preserved):
                    raise ValueError('Preserved branch needs a reason, not a feasibility verdict')

    def call(self, sid, role, task, context, notes=False):
        researcher = role in self.questions.researchers
        initial = sid in {f'01_initial_{i}' for i in range(len(RESEARCHERS))} and researcher
        independent = sid.startswith('01_initial_') and researcher
        context = {**context, '_stage': sid}
        if researcher:
            context['researcher'] = role
            context['memory'] = self.packet(sid, role)
            context['evidence_state'] = self.evidence.history_packet(sid, independent=independent)
            context['hypothesis_state'] = self.hypotheses.packet(sid, role, independent=independent)
            task += '\n' + EVIDENCE_PROTOCOL + '\n' + LEARNING_REQUEST + '\n' + HYPOTHESIS_PROTOCOL
            if not initial:
                context['question_state'] = self.questions.packet(sid, role)
                if independent:
                    context['question_state']['peer_questions'] = []
                    context['question_state']['shared_question'] = None
                    save(self.questions.root / 'inputs' / (sid + '.json'), context['question_state'])
                    task += '\nIndependent foundation learning: shared_question_update must be null.'
                task += '\n' + QUESTION_PROTOCOL
        if researcher:
            task += '\n' + NOTE_SCHEMA.replace('1-3 reusable notes', '0-3 reusable notes; [] when understanding did not change')
            task += '\nRetain correction sources. Preserve usable concepts/examples; do not rewrite a generic limitation without an actual change.'
        context['task_boundary'] = {'knowledge_before_exclusive': self.config['knowledge_before_exclusive'], 'raw_measurement_exception': self.config['raw_measurement_exception']}
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
        admission = root / 'admission.json'
        if admission.exists():
            pending = load(admission)
            if pending['input_sha256'] != fingerprint or pending['output_sha256'] != digest(path):
                raise ValueError('Pending admitted stage changed')
            return self.commit_stage(sid, role, load(path), path, context, initial, pending)
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
        if researcher:
            result = admit_reference_layout(result, sid, self.broker)
        try:
            self.validate(sid, role, result, context, notes, initial)
        except ValueError as error:
            repair = prompt + '\nSCHEMA REPAIR ONLY. Preserve scientific content. Fix only field layout, exact refs, allowed source strings or required metadata. Do not add claims or interpretations. Error: ' + str(error) + '\nUNADMITTED ANSWER:\n' + json.dumps(result, ensure_ascii=False)
            raw = invoke(repair, root / f'attempt-{number:03d}', self.timeout)
            result = ExistingPilot.admit_bookkeeping(raw, researcher, context.get('targets') if role == 'internal_evidence_verifier' else None)
            if researcher:
                result = admit_reference_layout(result, sid, self.broker)
            self.validate(sid, role, result, context, notes, initial)
        pending = {'input_sha256': fingerprint,
                   'note_dependencies': prepare_dependencies(self, result, context)}
        save(path, result)
        pending['output_sha256'] = digest(path)
        save(admission, pending)
        return self.commit_stage(sid, role, result, path, context, initial, pending)

    def commit_stage(self, sid, role, result, path, context, initial, pending):
        """Finish a previously validated stage idempotently after an interrupted write."""
        if result.get('memory_notes'):
            self.memory.commit(role, self.task_id, sid, path)
            self.record_note_dependencies(role, result, context, pending['note_dependencies'])
        if role in self.questions.researchers:
            self.questions.accept(sid, role, result, path, context.get('question_state'), initial)
            self.hypotheses.accept(sid, role, result, path, context.get('hypothesis_state'))
            self.evidence.observe(sid, role, result, path)
        self.state['stages'][sid] = {'input_sha256': pending['input_sha256'], 'output_sha256': digest(path)}
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
        report = self.call(sid, 'internal_evidence_verifier', '''Check only target statements using the supplied original evidence and computations. Return findings [{claim_ref,status:supported/needs_correction/undetermined,reason,evidence_refs:exact evidence_catalog keys,corrected_claim:scoped text or null}]. Check the whole inference AND the actual research consequence: inability to identify a behavior mechanism does not by itself imply that operational descriptions, conditional comparisons or further data analysis have no value. A correlation or time lag does not itself identify influence or physiological mechanism. Raw and smoothed derivatives differ. Missing evidence for a conjecture is not a refutation. No novelty or idea acceptance verdict. claims may be [].''', packet)
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
            result = self.call(sid, rid, UPTAKE_TASK.replace('Update memory_notes for EVERY supplied affected note', 'Update memory_notes for affected notes whose support, correction or dispute actually changed; for unchanged supported notes, [] is valid. Any revision uses its SAME key. For each changed note').replace('Even if affected_notes is empty, save at least one sourced correction/dispute note about\nyour actual response to this report, with kind correction and verification_report_path.', 'If nothing changed, explain that in the response; do not duplicate a generic limitation note.'), {'verification_report': report,
                     'verification_report_path': str(report_path.resolve()), 'affected_claims': affected,
                     'earlier_peer_responses': responses, **load(inputs)}, notes=True)
            responses.append({'researcher': rid, 'result': result, 'learning': self.service(sid, rid, result)})
        save(self.run / 'internal_verification/discussion' / (boundary+'.json'), responses)
        return responses

    def plan_analysis(self, task, protocol, root):
        prompt = (COMMON + "\nYou are the execution controller, translating ONLY the researcher's "
                  "requested computation. Preserve their question, variables, comparisons and record. "
                  "Do not invent a mechanism or choose a scientific answer. Return JSON {plan:analysis plan} "
                  "or {unavailable:concrete missing capability}.\n" + protocol + "\nREQUEST:\n" + json.dumps(task, ensure_ascii=False))
        attempts = len(list(root.glob('planner-attempt-*'))) + 1
        result = invoke(prompt, root / f'planner-attempt-{attempts:03d}', self.timeout)
        if not isinstance(result.get('plan'), dict):
            raise ValueError(result.get('unavailable', 'No executable plan'))
        return result['plan']

    def record_note_dependencies(self, rid, result, context, prepared=None):
        prepared = prepare_dependencies(self, result, context) if prepared is None else prepared
        path = self.broker.root / 'note_reviews.json'
        reviews = load(path) if path.exists() else {}
        for note in result.get('memory_notes', []):
            item = self.memory.index(rid)['notes'][note['key']]
            stored = load(item['path'])
            if stored['source_task'] != self.task_id or stored['source_stage'] != context['_stage']:
                raise ValueError('Committed note version moved before dependency registration')
            reviews[str(Path(item['path']).resolve())] = {**prepared[note['key']], 'sha256': item['sha256']}
        save(path, reviews)

    def service(self, sid, rid, answer):
        learned = []
        for hop in range(self.config['max_request_hops']):
            request = answer.get('learning_request', {'needed': False})
            if not request.get('needed'):
                break
            step = f'{sid}_learn_{hop}'
            path = self.run / 'broker' / (step + '.json')
            if not path.exists():
                save(path, self.broker.request(request, step))
            answer = self.call(step, rid, "Study the actual returned material/computation. Explain "
                "a useful concept or result with a worked example and scope. Return learning_change, "
                "remaining_gap, memory_notes and learning_request if another concrete gap remains. "
                "Differentiate read/explained/used. A failed search is not learning. For pending "
                "capability tasks preserve the question and hypothesis; conceptual development can continue. "
                "Explain whether the material changes an assumption or its consequences; no forced change. "
                "Illustrative hypothetical examples must not be presented as measured results.",
                {'your_request': request, 'broker_reply': load(path)}, notes=True)
            learned.append({'researcher': rid, 'result': answer})
        if answer.get('learning_request', {}).get('needed'):
            # Execute the final request too; retain its result for the next common discussion.
            step = f'{sid}_continuation_request'
            path = self.run / 'broker' / (step + '.json')
            if not path.exists():
                save(path, self.broker.request(answer['learning_request'], step))
            learned.append({'researcher': rid, 'continuation_material': load(path),
                            'status': 'read_return_pending_next_discussion'})
        return learned

    def execute(self):
        initial, history, corrections, learning = [], [], [], []
        initial_context = self.run / 'initial_materials.json'
        if not initial_context.exists():
            save(initial_context, {'measurement_metadata': self.broker.catalog,
                'sampled_windows': self.broker.request({'operations': [
                    {'kind': 'window', 'record_id': r, 'start': 1000, 'stop': 1160, 'stride': 4}
                    for r in ('R01', 'R07', 'R13')]}, 'initial_windows'),
                'source_catalog': [self.broker.sources[k] for k in sorted(self.broker.sources)]})
        for i, (rid, domain) in enumerate(RESEARCHERS):
            sid = f'01_initial_{i}'
            answer = self.call(sid, rid, "Study available foundations and screened measurement context. "
                "Return observation, expectation, expectation_basis, conditions, initial_question, "
                "question_to_peers, worked_example and memory_notes. Identify specific foundational "
                "gaps, models or examples you need for this question; use learning_request to acquire "
                "them when useful. You may propose operational definitions and change them. "
                "If a phenomenon or difficulty suggests an assumption, state and explore it as a hypothesis; "
                "its feasibility and proof are outside this discussion task.",
                {**load(initial_context), 'domain': domain}, notes=True)
            initial.append({'researcher': rid, 'result': answer})
            # Independent initial learning sees no peer questions or evidence.
            learning.extend(self.service(sid, rid, answer))
        for round_id in range(1, self.config['max_rounds'] + 1):
            exchanges, learned = [], []
            for i, (rid, _) in enumerate(RESEARCHERS):
                sid = f'r{round_id}_exchange_{i}'
                answer = self.call(sid, rid, "Respond to specific peer statements and pursue a useful "
                    "question or assumption. Return response_to_peers, changed_understanding, branches and exploration. "
                    "Develop the conceptual content of a specific hypothesis: what relationship or default "
                    "assumption changes, and what follows if the proposal holds. Keep alternative lines. "
                    "Advance a concrete uncertainty through theory, an example/counterexample, an "
                    "observation definition, conditions, or analysis. Explain the actual reason for "
                    "unchanged understanding. Consider the supplied progress state; repeating a general "
                    "limit is not a new observation. You can explicitly park a branch.",
                    {'initial': initial, 'foundational_learning': learning, 'previous_rounds': history,
                     'internal_discussions': corrections, 'earlier_exchanges_this_round': exchanges,
                     'progress': history[-1]['progress'] if history else None})
                exchanges.append({'researcher': rid, 'result': answer})
                learned.extend(self.service(sid, rid, answer))
            corrections.extend(self.verification(f'r{round_id}_evidence'))
            returned = []
            for i, (rid, _) in enumerate(RESEARCHERS):
                sid = f'r{round_id}_return_{i}'
                answer = self.call(sid, rid, "Return to common discussion with actual learned material "
                    "and results. Return changed_because, branches, memory_notes and exploration. "
                    "Develop or revise an assumption, its conceptual move and conditional consequences when useful. "
                    "Revise a definition, comparison, concept scope or question when useful. Preserve "
                    "unfinished hypotheses and explain why a parked branch can or cannot resume.",
                    {'initial': initial, 'prior_rounds': history, 'exchanges': exchanges,
                     'learning': learned, 'internal_discussions': corrections, 'earlier_returns': returned}, notes=True)
                returned.append({'researcher': rid, 'result': answer})
                learned.extend(self.service(sid, rid, answer))
            progress = self.progress(round_id, exchanges, returned, learned)
            history.append({'round': round_id, 'exchanges': exchanges, 'learning': learned,
                            'returned': returned, 'progress': progress})
            save(self.run / 'progress' / f'round_{round_id}.json', progress)
            if progress['disposition'] == 'park_with_explicit_reasons':
                break
        rid = RESEARCHERS[-1][0]
        fresh = self.call('04_fresh_continuation', rid, "Fresh session: use current screened notes "
            "and explicit question/hypothesis versions, without the full dialogue. Return memory_use "
            "[{key,version,source_task,scope_check}], continuation_question, worked_example and "
            "remaining_gap. Continue the actual saved line, including unfinished assumptions and consequences.", {'measurement_metadata': self.broker.catalog})
        learning.extend(self.service('04_fresh_continuation', rid, fresh))
        ideas = self.call('05_candidates', 'discussion_recorder', "Record 0-4 actual ideas, including "
            "unfinished ones. Return ideas [{id,title,idea,motivation,emergence,supporting_claim_refs}], "
            "question_trajectory and preserved_branches. Preserve corrections and actual changes. "
            "Do not strengthen a question beyond the discussion. Faithfully preserve each recorded "
            "assumption, conceptual move and conditional consequence; do not reduce it to a whether-question "
            "or promote it to an established finding. Do not select by feasibility, proof or evidence strength. "
            "preserved_branches: [{ref: exact supplied hypothesis ref, reason: faithful disposition}] "
            "must account for ALL current_hypotheses, including "
            "parked/incomplete branches and those not selected among the 0-4 ideas.",
            {'initial': initial, 'rounds': history, 'learning': learning, 'internal_discussions': corrections,
             'fresh': fresh, **self.questions.history_packet('05_candidates'),
             **self.hypotheses.history_packet('05_candidates')})
        save(self.run / 'ideas.json', ideas)
        freeze = self.run / 'GENERATION_FREEZE.json'
        if not freeze.exists():
            paths = [self.run / 'ideas.json']
            for sub in ('stages', 'broker', 'services', 'question_state', 'hypothesis_state', 'internal_verification', 'memory_retrieval', 'progress'):
                paths.extend(p for p in (self.run / sub).rglob('*') if p.is_file() and '06_final_check' not in str(p))
            save(freeze, {'files': {str(p.resolve()): digest(p) for p in paths},
                          'external_feedback_used_for_generation': False})
        memory_before = {str(p): digest(p) for p in self.memory.root.rglob('*.json')}
        checked = evaluate_final(self, ideas['ideas'])
        save(self.run / 'check_report.json', checked)
        if memory_before != {str(p): digest(p) for p in self.memory.root.rglob('*.json')}:
            raise ValueError('Final evaluator modified memory')
        for path, expected in load(freeze)['files'].items():
            if digest(path) != expected:
                raise ValueError('Frozen generation changed')
        save(self.run / 'EVALUATION_ISOLATION.json', {'memory_unchanged': True,
             'researcher_calls_after_evaluation': 0, 'generation_freeze_sha256': digest(freeze)})
        self.state['status'] = 'complete'
        save(self.state_path, self.state)
        self.audit()

    def progress(self, round_id, exchanges, returned, learned):
        values = [r['result'].get('exploration', {}) for r in exchanges + returned]
        unresolved = [str(p.resolve()) for p in (self.run / 'services/analysis').glob('*/controller_task.json')
                      if load(p).get('status') == 'pending_controller']
        question_changed = any(r['result'].get(field, {}).get('action') in {'revise', 'propose'}
                               for r in exchanges + returned for field in ('personal_question_update', 'shared_question_update')
                               if isinstance(r['result'].get(field), dict))
        hypothesis_changes = [u for e in self.hypotheses.events()
                              if e['stage'].startswith(f'r{round_id}_') for u in e['updates']]
        stalled = bool(values) and not question_changed and not hypothesis_changes and all(v.get('stalled_reason') and not v.get('understanding_changed') for v in values)
        return {'round': round_id, 'learning_events': len(learned), 'researcher_progress': values,
                'hypothesis_changes': [u['ref'] for u in hypothesis_changes],
                'pending_controller_tasks': unresolved,
                'disposition': 'park_with_explicit_reasons' if stalled and not learned else 'continue_with_next_actions',
                'boundary': 'Parking or a controller capability gap is not a scientific impossibility.'}

    def audit(self):
        verify(self.case)
        protected = load(self.run / 'PRESERVED_RECORDS.json')
        changed = [p for p, expected in protected.items() if digest(p) != expected]
        events = [load(p) for p in (self.run/'stages').glob('*/attempt-*/execution_audit.json')]
        reports = self.evidence.reports()
        source_tokens = tuple(self.config['excluded_dois'] + self.config['excluded_titles'])
        exposure = []
        for p in (self.run/'stages').glob('*/attempt-*/prompt.txt'):
            if any(t in p.read_text() for t in source_tokens):
                exposure.append(str(p))
        result = {'status': 'pass' if not changed and not exposure and not sum(e['tool_events'] for e in events) else 'fail',
                  'protected_original_files': len(protected), 'changed_original_files': changed,
                  'forbidden_source_token_hits': exposure, 'tool_events': sum(e['tool_events'] for e in events),
                  'requested_models': sorted({e['requested_model'] for e in events}), 'raw_attempts': len(events),
                  'logical_stages': len(self.state['stages']), 'internal_verification_batches': len(reports),
                  'source_date_hash_checks_passed': all(not self.broker.policy.rejection(s) for s in self.broker.sources.values()), 'pretraining_exclusion_claimed': False,
                  'tool_audit_scope': 'Generation roles only; the post-freeze checker uses a separate retrieval workspace.',
                  'original_memory_implementation_changed': False}
        save(self.run/'AUDIT.json', result)
        if result['status'] != 'pass':
            raise ValueError('Preservation or supplied-input audit failed')
        print(json.dumps(result), flush=True)



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--timeout', type=int, default=240)
    parser.add_argument('--run-id', default='inquiry_v2')
    parser.add_argument('--config', type=Path, default=HERE / 'configs/fish_v2.json')
    parser.add_argument('--audit-only', action='store_true')
    args = parser.parse_args()
    if not args.run_id.replace('_', '').isalnum():
        parser.error('Use a safe run ID')
    prepare()
    with (CASE / '.run.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        pilot = InquiryPilot(timeout=args.timeout, run_id=args.run_id, config=load(args.config))
        pilot.audit() if args.audit_only else pilot.execute()
