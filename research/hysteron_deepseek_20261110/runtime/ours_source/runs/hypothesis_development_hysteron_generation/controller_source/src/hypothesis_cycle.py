"""Content-linked inquiry handoffs; validates provenance, never intellectual quality."""
from copy import deepcopy
import json

VERSION = 'hypothesis-cycle-v1'
PROTOCOL = '''
HYPOTHESIS CONTENT CYCLE:
Use development_cycle as a thinking context, not a demand to invent progress. Choose one
specific explanatory relation, construction, distinction or unresolved phenomenon from its
sources. Locate the conceptual gap: what connection/premise/consequence is still unclear?
Choose a next move because of this gap: learn, derive, connect, reframe, or hold. Explain why
that move could change understanding. For learning, use this gap in learning_request.gap and
why_now, and formulate targeted queries; do not request a broad survey merely to fill a stage.
In discussion, take up a peer's concrete relation and explain how your discipline extends,
challenges or changes its consequences. Generic agreement about controls or feasibility is
not a substitute; a measurement contribution is valid when its specific consequences matter.
Study returned services against the gap that requested them, including failures and pending
capabilities. Do not call retrieval success learning. If nothing changes, say so and preserve
the gap. Own previous_steps carry unfinished thinking across phases and sessions. When the
controller flags repeated_no_change, reconsider the missing connection, premise, or next
learning move; holding a branch is valid. The flag uses supplied peer content comparisons, not a quality verdict. A shared interpretation is normal.
Return development_step:{focus:{source:exact development_cycle.sources key,quote:exact excerpt},
gap:nonempty text, action:learn/derive/connect/reframe/hold, reason:nonempty text,
expected_change:text or null for hold,
uptake:[{source:exact source key,quote:exact excerpt or null only for unresolved,
effect:revise/extend/challenge/unchanged/unresolved,reason:how this affects the focus,
consequence:conditional consequence or null when none follows}],
outcome:{kind:relation/implication/clarification/unchanged/uncertain,
statement:what changed or did not, remaining_gap:text or null}}.
Account once for EACH service key in required_service_uptake. If peer_sources is nonempty,
engage at least one (unresolved with a reason is valid). Other uptake is optional. Quotes must
come from the named source; for published claims quote readable source content, not metadata.
For relation/implication outcomes, preserve the resulting claim in a hypothesis_update's
assumption or implications. This records an author's proposal, NOT confirmed novelty/progress.
No compulsory new relation, branch, agreement, data, experiment, proof or implementation.
'''


def texts(value):
    if isinstance(value, str):
        yield value
        try:
            parsed = json.loads(value)
        except (ValueError, TypeError):
            return
        if not isinstance(parsed, str):
            yield from texts(parsed)
    elif isinstance(value, dict):
        for item in value.values():
            yield from texts(item)
    elif isinstance(value, list):
        for item in value:
            yield from texts(item)


def anchored(quote, value):
    return isinstance(quote, str) and bool(quote.strip()) and any(quote in t for t in texts(value))


def context(sources, previous=(), peer_sources=(), service_sources=()):
    previous = deepcopy(list(previous)[-2:])
    reviews = []
    for path, body in sources.items():
        try:
            value = json.loads(body) if isinstance(body, str) else body
            review = value.get('progress_review') if isinstance(value, dict) else None
        except (ValueError, TypeError):
            review = None
        if isinstance(review,dict) and review.get('kind') in {'advance','clarification','repetition','uncertain'}:
            reviews.append({'source':path, **review})
    return {'version': VERSION, 'sources': deepcopy(sources), 'previous_steps': previous,
            'peer_sources': list(peer_sources), 'required_service_uptake': list(service_sources),
            'peer_progress_reviews':reviews[-2:],
            'repeated_no_change':len(reviews)>=2 and all(r['kind'] in {'clarification','repetition'} for r in reviews[-2:]),
            'author_reports_no_change':len(previous)==2 and all(p['step']['outcome']['kind'] in {'unchanged','uncertain'} for p in previous),
            'scope':'Content comparisons are peer judgments with provenance, not scientific quality scores.'}


def validate_step(result, packet):
    if packet.get('version') != VERSION:
        raise ValueError('Unknown hypothesis cycle protocol')
    step = result.get('development_step')
    if not isinstance(step, dict):
        raise ValueError('Return development_step, including unchanged/uncertain when appropriate')
    sources = packet['sources']
    focus = step.get('focus', {})
    if not isinstance(focus, dict) or focus.get('source') not in sources or (focus.get('quote') is not None and not anchored(
            focus.get('quote'), sources[focus['source']])):
        raise ValueError('Development focus must quote an actual supplied source')
    for name in ('gap', 'reason'):
        if not isinstance(step.get(name), str) or not step[name].strip():
            raise ValueError('Development '+name+' requires text')
    if step.get('action') not in {'learn', 'derive', 'connect', 'reframe', 'hold'}:
        raise ValueError('Unknown development action')
    expected = step.get('expected_change')
    if not (isinstance(expected, str) and expected.strip()) and not (
            step['action'] == 'hold' and expected is None):
        raise ValueError('Describe expected conceptual change; hold may use null')
    request = result.get('learning_request', {})
    if isinstance(request, dict) and request.get('needed'):
        if not request.get('context_ref'):
            request['context_ref']='development_step'  # Structural linkage; prose may be compressed or paraphrased.
    uptake = step.get('uptake')
    if not isinstance(uptake, list):
        raise ValueError('Development uptake must be an array')
    seen = set()
    for row in uptake:
        if not isinstance(row, dict):
            raise ValueError('Development uptake must contain objects')
        key = row.get('source')
        if not isinstance(key, str) or key not in sources or key in seen:
            raise ValueError('Uptake needs unique supplied source keys')
        seen.add(key)
        if row.get('effect') not in {'revise', 'extend', 'challenge', 'unchanged', 'unresolved'}:
            raise ValueError('Unknown uptake effect')
        if row.get('quote') is not None and not anchored(row.get('quote'), sources[key]):
            raise ValueError('Uptake quote must occur in the named source')
        if not isinstance(row.get('reason'), str) or not row['reason'].strip():
            raise ValueError('Explain uptake in relation to the conceptual gap')
        consequence = row.get('consequence')
        if consequence is not None and (not isinstance(consequence, str) or not consequence.strip()):
            raise ValueError('Consequence is text or null')
    if not set(packet['required_service_uptake']) <= seen:
        raise ValueError('Account for every returned service, including failures')
    if packet['peer_sources'] and not set(packet['peer_sources']) & seen:
        raise ValueError('Engage a specific peer contribution or explain unresolved uptake')
    outcome = step.get('outcome', {})
    if not isinstance(outcome, dict) or outcome.get('kind') not in {
            'relation', 'implication', 'clarification', 'unchanged', 'uncertain'}:
        raise ValueError('Unknown development outcome')
    if not isinstance(outcome.get('statement'), str) or not outcome['statement'].strip():
        raise ValueError('Describe the actual outcome')
    gap = outcome.get('remaining_gap')
    if gap is not None and (not isinstance(gap, str) or not gap.strip()):
        raise ValueError('Remaining gap is text or null')
    # Scientific outcomes remain addressable in the immutable stage result.
    # A separate hypothesis card is optional; verbatim duplication is not a provenance condition.


def portfolio_context(packet, owner):
    """Use only this direction's actual snapshot; retain the previous owner's open gap."""
    sources = {'direction': packet['direction'], 'own_hypotheses': packet['hypothesis_state']['self']}
    peers, services = [], []
    for row in packet.get('peer_drafts', []):
        if row['owner'] != owner:
            key = 'peer:'+row['stage']; sources[key] = row['result']; peers.append(key)
    for reply in packet.get('service_replies', []):
        key = 'service:'+reply['request_stage']; sources[key] = reply; services.append(key)
    previous = [{'stage': row['stage'], 'step': row['development_step']}
                for row in packet['direction'].get('development_history', [])
                if row['owner'] == owner and row.get('development_step')]
    return context(sources, previous, peers, services)
