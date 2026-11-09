"""Domain-independent provenance, learning services and internal worked-example checks."""
from __future__ import annotations

from datetime import date, timedelta
import json
from pathlib import Path
import sys

import numpy as np

from discover import PROJECT, inside, read, write
from learning_memory import digest

sys.path.insert(0, str(PROJECT/'historical_inquiry'))
from question_state import QuestionState, PROTOCOL as QUESTION_PROTOCOL, object_hash
from hypothesis_development import HypothesisState, PROTOCOL as HYPOTHESIS_PROTOCOL
from knowledge_broker import KnowledgeBroker, SourcePolicy
from analysis_executor import expression
from request_routing import service_request


LEARNING_PROTOCOL = """
Optional learning_request: {needed:boolean, gap, why_now, queries:[strings],
urls:[], source_ids:[], record_ids:[], operations:[]}.
The controller searches and returns actual readable content. Keep your own scientific query;
classify returned sources as directly relevant, transferable method, or irrelevant, with reasons.
Do not treat a successful download as understanding. No compulsory tool use.
For a small worked calculation use an operation {kind:"calculation", question,
bindings:{name: numeric scalar/array}, expression: numeric array expression,
expected: optional numeric value/array}. Available arithmetic, slices and named functions
include mean,sum,std,norm,diff,abs,sqrt. Define which rows/columns mean which entities.
Top-level analysis_plan also dispatches. needed:false disables literature search, not explicit
calculations. Unsupported requests return a pending capability task; no scientific rejection.
Keep purely tentative proposals in hypothesis_updates/next_actions, not execution fields.
"""

REVIEW_PROTOCOL = """
Inspect the supplied researcher outputs and worked-example artifacts. Check specific arithmetic,
entity/index meaning, contradictions and mistaken attribution; do not judge novelty, feasibility,
unproved hypotheses, or require experiments. Missing proof is not an error. Quote exact source text.
Return findings:[{id,source_stage,quote,kind:arithmetic/logic/attribution,
status:needs_correction/undetermined,reason,note_keys:[affected keys in that source result]}].
For arithmetic, attach calculation:{bindings:{name:numeric scalar/array},expression,
expected:numeric scalar/array}. The controller recomputes it. Carefully extract the source's
actual numbers and asserted result; do not invent a calculation to manufacture an error.
When before_inputs are supplied, compare learning-change claims to the actual prior memory and
materials. Rewording an already supplied distinction is not a new relation; a new application may
be substantive. Prior availability is not proof of internal mastery.
An arbitrary prose inference cannot be certified by this numerical check. findings:[] is valid.
"""


def material_coverage(result):
    """Check evidence declarations and exact excerpts, not scientific truth or completeness."""
    sources = result.get('sources', [])
    usable, issues = [], []
    for s in sources:
        path = inside(s['local_path'])
        if not path.is_file():
            raise ValueError('Missing downloaded source')
        quote = s.get('supporting_quote', '')
        readable = s.get('content_access') in {'abstract', 'full_text', 'excerpt'}
        direct = s.get('domain_relation') == 'direct' and bool(s.get('relevance_reason'))
        if readable and direct and isinstance(quote, str) and quote.strip() and quote in path.read_text(errors='replace'):
            usable.append({**s, 'content_sha256': digest(path)})
        else:
            issues.append({'source_id': s.get('id'), 'reason': 'Missing direct readable content and exact supporting excerpt'})
    primary = [s for s in usable if s.get('source_kind') == 'original_study']
    foundation = [s for s in usable if s.get('source_kind') in {'review', 'textbook'}]
    independent = any(a.get('url') != b.get('url') and a['content_sha256'] != b['content_sha256']
                      for a in primary for b in foundation)
    gaps = ([] if primary else ['readable_original_study']) + ([] if independent else ['independent_domain_foundation'])
    return {'status': 'covered' if not gaps else 'incomplete', 'missing': gaps, 'source_issues': issues,
            'scope': 'Source declarations and excerpt integrity only; domain adequacy still requires researcher judgment.'}


def calculation(op):
    if op.get('kind') != 'calculation':
        return {'status': 'pending_controller', 'reason': 'Generic runner supports explicit worked calculations only; a dataset adapter is needed.', 'request': op}
    try:
        bindings = op.get('bindings', {})
        if not isinstance(bindings, dict) or len(bindings) > 32:
            raise ValueError('Bounded numeric bindings required')
        env = {}
        for key, value in bindings.items():
            if not isinstance(key, str) or not key.isidentifier() or key.startswith('_'):
                raise ValueError('Invalid binding name')
            array = np.asarray(value)
            if array.dtype.kind not in 'biuf' or array.size > 10000 or not np.isfinite(array).all():
                raise ValueError('Finite bounded numeric bindings required')
            env[key] = array
        actual = np.asarray(expression(op['expression'], env))
        if actual.dtype.kind not in 'biuf' or actual.size > 10000 or not np.isfinite(actual).all():
            raise ValueError('Calculation must produce finite bounded numeric output')
        match = None
        if 'expected' in op:
            expected = np.asarray(op['expected'], dtype=float)
            match = expected.shape == actual.shape and bool(np.allclose(actual, expected, rtol=1e-9, atol=1e-9))
        return {'status': 'executed', 'actual': actual.tolist(), 'matches_expected': match,
                'scope': 'Recomputation of supplied expression/bindings; extraction and scientific interpretation require review.'}
    except (ValueError, TypeError, KeyError, IndexError, SyntaxError, OverflowError) as error:
        return {'status': 'pending_controller', 'reason': str(error), 'request': op}


class LearningServices:
    def __init__(self, run, config=None, fetch=None):
        self.run = Path(run)
        policy = config or default_policy()
        self.knowledge = KnowledgeBroker(self.run/'services/knowledge', SourcePolicy(policy), fetch)

    def reply(self, stage, answer):
        answer = dict(answer)
        if isinstance(answer.get('learning_request'), dict):
            req = dict(answer['learning_request'])
            if 'queries' not in req and 'search_terms' in req:
                req['queries'] = req['search_terms']
            answer['learning_request'] = req
        request, routing = service_request(answer)
        if not request['needed']:
            return None
        development_context = answer.get('development_step')
        path = self.run/'services/replies'/(stage+'.json')
        if path.exists():
            old = read(path)
            if (old['request'] != request or old['routing'] != routing
                    or old.get('development_context') != development_context):
                raise ValueError('Learning request changed')
            return path
        knowledge = []
        selected, unavailable = [], []
        for sid in request.get('source_ids', []):
            if sid in self.knowledge.sources:
                selected.append(self.knowledge.sources[sid])
            else:
                unavailable.append({'source_id': sid, 'reason': 'Unknown source ID in this run'})
        for rid in request.get('record_ids', []):
            unavailable.append({'record_id': rid, 'reason': 'No tabular record adapter configured; use supplied materials or an explicit worked calculation'})
        if routing['knowledge_requested'] and (request.get('queries') or request.get('gap') or request.get('urls')):
            search_request = dict(request)
            if not request.get('queries') and not request.get('gap'):
                search_request['queries'] = request['urls']
                search_request['urls'] = []
            for attempt in range(2):
                result = self.knowledge.search(search_request, stage+f'_search_{attempt}')
                knowledge.append(result)
                if result['sources']:
                    break
        computed = [{'request': op, 'result': calculation(op)} for op in request['operations']]
        sources = {s['id']: s for s in [*selected, *[s for r in knowledge for s in r['sources']]]}
        write(path, {'request_stage': stage, 'development_context': development_context,
                     'request': request, 'routing': routing, 'knowledge_attempts': knowledge,
                     'sources': list(sources.values()), 'computed': computed, 'unavailable': unavailable,
                     'status': 'returned', 'knowledge_status': 'readable_sources_returned' if sources
                     else ('unresolved' if knowledge else 'not_requested')})
        return path


def review_packet(stage_results, before_inputs=None):
    sources = {}
    for stage, (owner, path) in stage_results.items():
        path = Path(path)
        files = [path, *sorted(path.parent.glob('*.md'))]
        sources[stage] = {'owner': owner, 'result': read(path), 'path': str(path),
                          'files': [{'path': str(p), 'sha256': digest(p),
                                     'text': p.read_text(errors='replace')[:100000]} for p in files]}
        sources[stage]['before_inputs'] = [
            {'path': str(p), 'sha256': digest(p), 'text': Path(p).read_text(errors='replace')}
            for p in (before_inputs or {}).get(stage, [])]
    return {'sources': sources, 'scope': 'Actual supplied inputs and outputs; availability is not proof of mastery; final evaluation excluded.'}


def audit_review(result, packet):
    findings = result.get('findings')
    if not isinstance(findings, list):
        raise ValueError('Internal review requires findings array')
    rows, ids = [], set()
    for f in findings:
        source = packet['sources'].get(f.get('source_stage'))
        if not source or not isinstance(f.get('id'), str) or not f['id'] or f['id'] in ids:
            raise ValueError('Review needs unique finding IDs and actual source stage')
        ids.add(f['id'])
        if not isinstance(f.get('quote'), str) or not f['quote'].strip() or not any(f['quote'] in p['text'] for p in source['files']):
            raise ValueError('Review quote must occur in its named source')
        if f.get('status') not in {'needs_correction', 'undetermined'} or f.get('kind') not in {'arithmetic', 'logic', 'attribution'} or not f.get('reason'):
            raise ValueError('Invalid internal finding')
        keys = {n['key'] for n in source['result'].get('memory_notes', [])}
        if not isinstance(f.get('note_keys'), list) or not set(f['note_keys']) <= keys:
            raise ValueError('Review may name only notes from its source')
        checked = calculation({'kind': 'calculation', **f['calculation']}) if f.get('calculation') else None
        status = f['status']
        if f['kind'] == 'arithmetic':
            # Reviewer confidence is not an independent numerical check.
            if not checked or checked['status'] != 'executed' or checked['matches_expected'] is not False:
                status = 'undetermined'
        rows.append({**f, 'status': status, 'owner': source['owner'], 'recomputation': checked})
    return {'findings': rows, 'source_packet_sha256': object_hash(packet),
            'scope': 'Specific process errors; not hypothesis acceptance or novelty evaluation.'}


def default_policy():
    return {'knowledge_before_exclusive': (date.today()+timedelta(days=1)).isoformat(),
            'excluded_dois': [], 'excluded_titles': [],
            'retrieval_results_per_query': 4, 'read_full_text': True}


def validate_uptake(result, report, owner, report_path=None):
    findings = {f['id']: f for f in report['findings']}
    replies = result.get('verification_responses', [])
    if not isinstance(replies, list) or any(not isinstance(r, dict) for r in replies):
        raise ValueError('verification_responses must be an array of objects')
    if len(replies) != len(findings) or {r.get('finding_id') for r in replies} != set(findings):
        raise ValueError('Respond to every supplied internal finding')
    for reply in replies:
        if reply.get('stance') not in {'accept', 'rebut', 'unresolved'} or not reply.get('reason'):
            raise ValueError('Internal response needs stance and reason')
        f = findings[reply['finding_id']]
        if f['owner'] != owner:
            continue
        notes = {n['key']: n for n in result.get('memory_notes', [])}
        for key in f['note_keys']:
            n = notes.get(key, {})
            if n.get('kind') != 'correction' or not n.get('revision_reason'):
                raise ValueError('Affected own note needs same-key correction/dispute version')
            if report_path is not None and str(report_path) not in n.get('sources', []):
                raise ValueError('Correction/dispute note must cite the internal report')
