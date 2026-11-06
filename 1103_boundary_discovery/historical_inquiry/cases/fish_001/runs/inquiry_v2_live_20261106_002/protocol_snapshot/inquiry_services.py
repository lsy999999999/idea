"""Open request broker and provenance-screened persistent note retrieval."""
from __future__ import annotations

import json
from pathlib import Path

from analysis_executor import AnalysisExecutor
from fish_materials import Broker, PROPOSAL, digest
from knowledge_broker import KnowledgeBroker, SourcePolicy
from note_dependencies import SCHEMA as DEPENDENCY_SCHEMA
from prepare import save


class InquiryBroker(Broker):
    def __init__(self, case, root, config, planner=None, fetch=None):
        super().__init__(case)
        self.root, self.policy = Path(root), SourcePolicy(config)
        self.knowledge = KnowledgeBroker(self.root / 'knowledge', self.policy, fetch)
        self.sources = {sid: s for sid, s in self.sources.items() if not self.policy.rejection(s)}
        self.sources.update(self.knowledge.sources)
        # Reuse only sources accepted under the SAME task policy from previous v2 runs.
        for path in sorted((self.case / 'runs').glob('*/services/knowledge/accepted/*.json')):
            source = json.loads(path.read_text())
            if not self.policy.rejection(source):
                self.knowledge.verify_identity(source)
                self.sources[source['id']] = source
        self.executor = AnalysisExecutor(self, self.root / 'analysis', planner)
        self.catalog = {**self.catalog, 'measurement_context': self.measurement_context()}

    def measurement_context(self):
        """Field-level curated data facts; no originating abstract/body is copied."""
        raw = PROPOSAL / 'controller_only/paired_data.json'
        metadata = json.loads(raw.read_text())
        if 'Danio rerio' not in metadata.get('keywords', []):
            raise ValueError('Species provenance changed; review context before use')
        restriction = json.loads((self.case / 'controller_only/restriction.json').read_text())
        return {
            'data_source': {'repository': 'Dryad', 'doi': restriction['data_doi'],
                            'license': metadata['license'], 'publication_date': metadata['publicationDate'],
                            'scope': 'Raw measurements and screened measurement facts are the task date exception.'},
            'species': {'value': 'Danio rerio (zebrafish)', 'basis': 'Data repository species keyword'},
            'recording': '13 records of two tracked fish; positions and tracker outputs, no supplied manipulation labels.',
            'task': {'value': None, 'status': 'Specific experimental task/protocol not independently verified in screened metadata.'},
            'scene_conditions': {'value': None, 'status': 'Arena geometry, lighting, age and preparation unknown from screened measurement sources.'},
            'measurement_method': 'Recorded two dimensional tracked image coordinates; camera/tracker implementation unspecified.',
            'processing': 'Archive arrays retained value-for-value, including NaN and negative tracker codes; no smoothing or quality exclusion.',
            'units': 'Native image coordinates and frame indices; physical scales/frame rate not independently verified.',
            'quality': self.catalog['score_meaning'],
            'screening': 'Only source-data identity, species keyword, license, date, field layout and measurement facts supplied.'}

    def check_basis(self, basis):
        if any(not isinstance(s, str) or s not in self.sources for s in basis.get('source_ids', [])):
            raise ValueError('Unavailable source ID')
        if any(not isinstance(r, str) or r not in self.records for r in basis.get('record_ids', [])):
            raise ValueError('Unavailable record ID')

    def request(self, request, request_id=None):
        if not isinstance(request, dict):
            raise ValueError('Request must be an object')
        self.check_basis(request)
        if request_id is None:
            import hashlib
            request_id = 'request_' + hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()[:16]
        sources = [self.sources[s] for s in request.get('source_ids', [])]
        knowledge = None
        # Knowledge/gap requests go online automatically, including requests without seed IDs.
        if request.get('queries') or request.get('urls') or request.get('knowledge') or (request.get('needed') and request.get('gap') and not request.get('operations')):
            knowledge = self.knowledge.search(request, request_id)
            self.sources.update(self.knowledge.sources)
            sources.extend(knowledge['sources'])
        computations = [self.executor.execute(op, request_id + f'_op{i}')
                        for i, op in enumerate(request.get('operations', []))]
        pending = [c['result']['capability_task'] for c in computations if c['result'].get('status') == 'pending_controller']
        return {'request': request, 'sources': sources, 'knowledge': knowledge,
                'record_metadata': [self.records[r] for r in request.get('record_ids', [])],
                'computed': computations, 'controller_pending': pending,
                'unavailable': [], 'measurement_context': self.catalog['measurement_context']}


class NoteGate:
    """Screen every source dependency, use current versions, retain excluded stores intact."""
    def __init__(self, broker, roots):
        self.broker, self.roots = broker, [Path(r) for r in roots]

    def review_frozen_note(self, note, item):
        """Audit the source closure of the earlier isolated fish run, not arbitrary old notes."""
        task = note.get('source_task', '')
        if not task.startswith(self.broker.case.name + '/'):
            return None
        run_id = task.split('/', 1)[1]
        if '/' in run_id or run_id in {'.', '..'}:
            return None
        run = self.broker.case / 'runs' / run_id
        setup_path, state_path = run / 'FROZEN_SETUP.json', run / 'state.json'
        if not setup_path.exists() or not state_path.exists():
            return None
        setup, state = json.loads(setup_path.read_text()), json.loads(state_path.read_text())
        if state.get('protocol') != 'fish-inquiry-v1':
            return None
        allowed = json.loads((self.broker.case / 'controller_only/allowed_hashes.json').read_text())
        if setup.get('allowed_sha256') != allowed:
            return None
        sources = json.loads((self.broker.case / 'allowed/sources.json').read_text())
        if any(self.broker.policy.rejection(source) for source in sources):
            return None
        source_path = Path(note['source_result'])
        record = state['stages'].get(note['source_stage'], {})
        if (run not in source_path.parents or digest(source_path) != note['source_sha256']
                or record.get('output_sha256') != note['source_sha256']):
            return None
        # Its complete supply closure was four screened sources plus measurements and
        # within-run evidence reports. Validate all citations and frozen actor tool audits.
        known = {s['doi'] for s in sources} | {'measurements.json'}
        for citation in note.get('sources', []):
            if citation in known:
                continue
            match = next((v for v in state['stages'].values() if
                          Path(citation).is_file() and v['output_sha256'] == digest(citation)), None)
            if run not in Path(citation).parents or not match:
                return None
        audits = list((run / 'stages').glob('*/attempt-*/execution_audit.json'))
        if not audits or any(json.loads(p.read_text()).get('tool_events') != 0 for p in audits):
            return None
        return {'sha256': item['sha256'], 'content_screened': True, 'dependency_schema': DEPENDENCY_SCHEMA,
                'source_dependencies': sorted(known),
                'basis': 'Frozen isolated fish-v1 source closure, output hash and zero-tool audit; excluded-content scan applied separately.'}

    def retrieve(self, rid, query, output, limit=8):
        from learning_memory import tokens
        accepted, rejected, seen = [], [], set()
        source_map = {s['doi']: s for s in self.broker.sources.values()}
        data_sources = {'measurements.json', self.broker.catalog['measurement_context']['data_source']['doi']}
        for root in self.roots:
            index = root / rid / 'index.json'
            if not index.exists():
                continue
            for key, item in json.loads(index.read_text()).get('notes', {}).items():
                path = Path(item['path'])
                if digest(path) != item['sha256']:
                    raise ValueError('Memory hash changed')
                note = json.loads(path.read_text())
                if digest(note['source_result']) != note['source_sha256']:
                    raise ValueError('Memory originating result hash changed')
                # A note may contain interpretations beyond its citations; old task notes need
                # an explicit field/content review, never infer eligibility from an old DOI alone.
                review_path = self.broker.root / 'note_reviews.json'
                reviews = {}
                for previous in sorted((self.broker.case / 'runs').glob('*/services/note_reviews.json')):
                    reviews.update(json.loads(previous.read_text()))
                if review_path.exists():
                    reviews.update(json.loads(review_path.read_text()))
                review = reviews.get(str(path.resolve()), {})
                if review.get('dependency_schema') != DEPENDENCY_SCHEMA:
                    review = self.review_frozen_note(note, item) or {}
                reviewed = (review.get('sha256') == item['sha256'] and review.get('content_screened') is True
                            and review.get('dependency_schema') == DEPENDENCY_SCHEMA)
                deps = review.get('source_dependencies', note.get('sources', []))
                reason = None
                if self.broker.policy.forbidden(note):
                    reason = 'excluded_content'
                elif not reviewed:
                    reason = 'prior_note_content_and_dependencies_need_review'
                elif not deps:
                    reason = 'missing_source_dependencies'
                elif any(s not in data_sources and (s not in source_map or self.broker.policy.rejection(source_map[s])) for s in deps):
                    reason = 'unverified_source_dependency'
                if reason:
                    rejected.append({'path': str(path), 'sha256': item['sha256'], 'reason': reason})
                    continue
                if key in seen:
                    continue
                seen.add(key)
                score = len(tokens(query) & tokens(json.dumps(note, ensure_ascii=False)))
                accepted.append({'overlap_score': score, 'note': note, 'source_dependencies': deps,
                                 'dependency_schema': DEPENDENCY_SCHEMA,
                                 'scope_check': 'Content and all declared scientific dependencies pass this task policy.'})
        accepted.sort(key=lambda n: -n['overlap_score'])
        save(Path(output).parent.parent / 'controller_only/note_screening' / Path(output).name,
             {'accepted_paths': [{'path': n['note']['source_result'], 'source_dependencies': n['source_dependencies']} for n in accepted], 'excluded': rejected})
        result = {'researcher': rid, 'query': query, 'method': 'Current versions, task source/dependency screen, then lexical overlap',
                  'retrieved': accepted[:limit]}
        save(output, result)
        return result
