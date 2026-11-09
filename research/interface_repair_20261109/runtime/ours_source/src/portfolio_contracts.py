"""Auditable contracts for development assessment; no numerical idea-quality score."""
from itertools import combinations
import json
from pathlib import Path

from discover import read


def text_values(value):
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for v in value.values() for s in text_values(v)]
    if isinstance(value, list):
        return [s for v in value for s in text_values(v)]
    return []


def require_text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(label + ' requires nonempty text')


def anchored(quote, content):
    return isinstance(quote, str) and bool(quote.strip()) and any(quote in s for s in text_values(content))


def envelope(result, workspace):
    require_text(result.get('summary'), 'summary')
    for key in ('artifacts', 'evidence', 'claims', 'limitations', 'next_actions'):
        if not isinstance(result.get(key), list):
            raise ValueError(key + ' must be an array')
    if not result['artifacts']:
        raise ValueError('Save an actual artifact')
    for item in result['artifacts']:
        raw = item.get('path') if isinstance(item, dict) else item
        if not isinstance(raw, str):
            raise ValueError('Artifact path must be text')
        path = Path(raw)
        path = (workspace / path).resolve() if not path.is_absolute() else path.resolve()
        if not path.is_relative_to(workspace.resolve()) or not path.is_file():
            raise ValueError('Artifact must be an existing file in assigned workspace')


def validate_ranker(result, packet):
    directions = {d['id']: d for d in packet['directions']}
    assessments = result.get('assessments', [])
    if len(assessments) != len(directions) or {a.get('direction_id') for a in assessments} != set(directions):
        raise ValueError('Assess every supplied direction exactly once')
    for a in assessments:
        content = directions[a['direction_id']]
        for dim in ('problem', 'conceptual_move', 'development_space'):
            row = a.get(dim, {})
            if row.get('status') not in {'articulated', 'unclear'}:
                raise ValueError('Dimension status must be articulated/unclear')
            require_text(row.get('reason'), dim)
            quotes = row.get('quotes')
            if not isinstance(quotes, list) or any(not anchored(q, content) for q in quotes):
                raise ValueError('Ranker quotes must occur in that direction')
            if row['status'] == 'articulated' and not quotes:
                raise ValueError('Articulated judgment requires original-text anchors')
        require_text(a.get('uncertainty'), 'uncertainty')
        if any(k in a for k in ('score', 'total_score', 'feasibility_score')):
            raise ValueError('No invented scalar quality/feasibility score')
        possibilities = a.get('future_possibilities', [])
        if not isinstance(possibilities, list):
            raise ValueError('future_possibilities must be an array')
        for p in possibilities:
            if p.get('origin') != 'ranker_conjecture':
                raise ValueError('Ranker future possibilities are projections, not existing contributions')
            require_text(p.get('text'), 'future possibility')
            if not p.get('basis_quotes') or any(not anchored(q, content) for q in p['basis_quotes']):
                raise ValueError('A projection needs an anchored connection')
    expected = {frozenset(p) for p in combinations(directions, 2)}
    seen = set()
    for c in result.get('comparisons', []):
        pair = frozenset((c.get('a'), c.get('b')))
        if pair not in expected or pair in seen:
            raise ValueError('Invalid or duplicate comparison pair')
        seen.add(pair)
        if c.get('preference') not in {'prefer_a', 'prefer_b', 'parallel', 'undetermined'}:
            raise ValueError('Invalid comparison preference')
        require_text(c.get('reason'), 'comparison reason')
        require_text(c.get('counterargument'), 'counterargument/uncertainty')
        evidence = c.get('anchors', [])
        if not isinstance(evidence, list) or {e.get('direction_id') for e in evidence} != set(pair):
            raise ValueError('Compare original content on BOTH sides')
        for e in evidence:
            if not anchored(e.get('quote'), directions[e['direction_id']]):
                raise ValueError('Invalid comparison quote')
    if seen != expected:
        raise ValueError('Missing comparison pairs; parallel/undetermined are valid')
    ids = set()
    for s in result.get('suggestions', []):
        if not isinstance(s.get('id'), str) or not s['id'] or s['id'] in ids:
            raise ValueError('Unique suggestion IDs required')
        ids.add(s['id'])
        if s.get('origin') != 'ranker_conjecture' or s.get('direction_id') not in directions:
            raise ValueError('Suggestion must identify direction and ranker origin')
        require_text(s.get('text'), 'suggestion')
        if not s.get('basis_quotes') or any(not anchored(q, directions[s['direction_id']]) for q in s['basis_quotes']):
            raise ValueError('Suggestion must connect to actual idea content')
    if result.get('memory_notes'):
        raise ValueError('Ranker judgments cannot write researcher knowledge')


def common_source_ids(common):
    """Accept both flat source records and frozen source-catalog file snapshots."""
    ids = set()
    for item in common:
        if not isinstance(item, dict):
            continue
        if isinstance(item.get('id'), str) and item['id']:
            ids.add(item['id'])
        catalog = item
        if isinstance(item.get('text'), str):
            try:
                catalog = json.loads(item['text'])
            except (TypeError, ValueError):
                continue
        if isinstance(catalog, dict) and isinstance(catalog.get('sources'), list):
            ids.update(s['id'] for s in catalog['sources'] if isinstance(s, dict)
                       and isinstance(s.get('id'), str) and s['id'])
    return ids


def validate_developer(result, packet):
    if 'development_cycle' in packet:
        from hypothesis_cycle import validate_step
        validate_step(result, packet['development_cycle'])
    if any(k in result for k in ('hypothesis_state', 'question_before', 'question_after',
                                  'personal_question_update', 'shared_question_update')):
        raise ValueError('Development uses scoped hypothesis_updates; question state is read-only')
    updates = result.get('hypothesis_updates')
    if not isinstance(updates, list):
        raise ValueError('Return top-level hypothesis_updates, [] is valid')
    prefix = packet['direction']['id'] + '__'
    own = {c['ref']['key']: c for c in packet['hypothesis_state']['self']}
    known = [c['ref'] for c in packet['hypothesis_state']['self'] + packet['hypothesis_state']['peer_branches']]
    seen = set()
    for card in updates:
        key = card.get('key', '')
        if not key.startswith(prefix) or key in seen or not key.replace('_', '').isalnum():
            raise ValueError('Update only unique hypothesis keys in your focus direction namespace')
        seen.add(key)
        if 'ref' in card or 'owner' in card:
            raise ValueError('Hypothesis ownership is controller assigned')
        base = own[key]['ref']['version'] if key in own else 0
        if type(card.get('base_version')) is not int or card['base_version'] != base:
            raise ValueError('Wrong hypothesis base version')
        for k in ('assumption', 'motivation', 'reason'):
            require_text(card.get(k), k)
        if card.get('conceptual_move') is not None and not isinstance(card['conceptual_move'], str):
            raise ValueError('Conceptual move is text or null')
        for k in ('implications', 'open_questions'):
            if not isinstance(card.get(k), list) or any(not isinstance(x, str) or not x.strip() for x in card[k]):
                raise ValueError(k + ' is a text array; empty is valid')
        if card.get('status') not in {'developing', 'parked'}:
            raise ValueError('Invalid hypothesis status')
        if not isinstance(card.get('influenced_by'), list) or any(r not in known for r in card['influenced_by']):
            raise ValueError('Hypothesis influences must be exact supplied hypothesis refs')
    expected = [s['ref'] for s in packet['feedback']['suggestions']]
    replies = result.get('feedback_responses', [])
    if len(replies) != len(expected) or any(sum(x.get('ref') == r for x in replies) != 1 for r in expected):
        raise ValueError('Account for each ranker suggestion with its exact ref')
    for r in replies:
        if r.get('stance') not in {'adopt', 'adapt', 'branch', 'decline', 'hold'}:
            raise ValueError('Invalid feedback stance')
        require_text(r.get('reason'), 'feedback reason')
    supplied = {s['id'] for reply in packet.get('service_replies', []) for s in reply['sources']}
    uses = result.get('source_use', [])
    common_ids = common_source_ids(packet.get('common', []))
    if not isinstance(uses, list) or any(not isinstance(x, dict) for x in uses):
        raise ValueError('source_use must be an array of objects')
    used_ids = [x.get('source_id') for x in uses]
    if len(set(used_ids)) != len(used_ids) or not supplied <= set(used_ids) or not set(used_ids) <= supplied | common_ids:
        raise ValueError('source_use must cover all service sources once; optional known common sources are allowed')
    for u in uses:
        if u.get('relation') not in {'direct', 'method', 'irrelevant', 'not_read'}:
            raise ValueError('Invalid source_use relation')
        require_text(u.get('reason'), 'source-use reason')
    from learning_support import service_request
    service_request(result)
    from learning_memory import validate_notes
    validate_notes(result.get('memory_notes', []), packet['memory']['available_index'])


def progress_baselines(source):
    """Relevant pre-step groups; the initial seed alone is not the comparison baseline."""
    groups = {}
    for f in source.get('before_inputs', []):
        try:
            packet = json.loads(f['text'])
        except (TypeError, ValueError):
            continue
        if not isinstance(packet, dict):
            continue
        def obj(key):
            value = packet.get(key, {})
            return value if isinstance(value, dict) else {}
        did = obj('direction').get('id')
        owner = obj('identity').get('id')
        candidates = {
            'current_self': [c for c in obj('hypothesis_state').get('self', [])
                             if not did or c['ref']['key'].startswith(did+'__')],
            'peer_drafts': [d for d in packet.get('peer_drafts', []) if d.get('owner') != owner],
            'ranker_feedback': obj('feedback').get('suggestions', []),
            'retrieved_memory': obj('memory').get('retrieved', []),
        }
        for group, content in candidates.items():
            if content:
                groups.setdefault(group, []).append(content)
    return groups


def validate_progress(result, packet):
    sources = packet['sources']
    changes = result.get('changes')
    if not isinstance(changes, list) or {c.get('stage') for c in changes} != set(sources):
        raise ValueError('Describe a change or uncertainty for every stage')
    from learning_support import audit_review
    audit_review(result, packet)
    if sorted(result.get('reviewed_stages', [])) != sorted(sources):
        raise ValueError('Progress reviewer must account for every supplied stage')
    for c in result.get('changes', []):
        source = sources.get(c.get('stage'))
        if source is None:
            raise ValueError('Unknown progress source stage')
        if c.get('classification') not in {'new_relation', 'new_application', 'correction', 'restatement', 'unclear'}:
            raise ValueError('Invalid change classification')
        if not anchored(c.get('after_quote'), [f['text'] for f in source['files']]):
            raise ValueError('Progress after quote must occur in actual output')
        require_text(c.get('reason'), 'progress reason')
        before = {f['path']: f['text'] for f in source.get('before_inputs', [])}
        anchors = c.get('before_evidence', [])
        if not anchors and c['classification'] != 'unclear':
            raise ValueError('Compare actual before inputs, not author self-report')
        for e in anchors:
            if e.get('path') not in before or not anchored(e.get('quote'), before[e['path']]):
                raise ValueError('Before quote must occur in the actual supplied input')
        if c['classification'] in {'new_relation', 'new_application', 'correction'}:
            missing = [group for group, content in progress_baselines(source).items()
                       if not any(anchored(e.get('quote'), content) for e in anchors)]
            if missing:
                raise ValueError('Progress baseline omits supplied groups: ' + ', '.join(missing))
        if c['classification'] == 'new_relation' and anchored(c['after_quote'], list(before.values())):
            raise ValueError('An identical already-supplied relation is not newly introduced')
    if result.get('memory_notes'):
        raise ValueError('Progress judgments are not researcher knowledge')


def validate(kind, result, packet, workspace):
    envelope(result, workspace)
    if kind == 'ranker':
        validate_ranker(result, packet)
    elif kind == 'developer':
        validate_developer(result, packet)
    elif kind == 'progress':
        validate_progress(result, packet)
    elif kind == 'uptake':
        from learning_support import validate_uptake
        from learning_memory import validate_notes
        if result.get('hypothesis_updates'):
            raise ValueError('Uptake does not overwrite hypothesis state')
        validate_uptake(result, packet['internal_review'], packet['owner'], packet['internal_review_path'])
        validate_notes(result.get('memory_notes', []), packet['memory']['available_index'])
    elif kind == 'recorder':
        from idea_check import validate_ideas
        if result.get('ideas'):
            validate_ideas(result)
            if any('evaluation_context' in i for i in result['ideas']):
                raise ValueError('Generator cannot assign evaluation context')
        elif result.get('ideas') != []:
            raise ValueError('Return ideas array')
        refs = [c['ref'] for c in packet['current_hypotheses']]
        got = [x.get('ref') for x in result.get('preserved_branches', [])]
        if len(refs) != len(got) or any(got.count(r) != 1 for r in refs):
            raise ValueError('Preserve every current branch ref, including parked directions')
        if sorted(result.get('preserved_directions', [])) != sorted(d['id'] for d in packet['directions']):
            raise ValueError('Preserve all directions, including unselected seeds')
    elif kind == 'checker':
        from idea_check import validate_checks
        validate_checks(result, packet['ideas'], require_claims=True)
    elif kind != 'generic':
        raise ValueError('Unknown role contract')
