"""Synthetic no-progress actor output for interface tests, never research evidence."""
from hypothesis_cycle import texts


def development_step(context):
    key = next(k for k, v in context['sources'].items() if list(texts(v)))
    quote = next(t for t in texts(context['sources'][key]) if t.strip())
    needed = list(dict.fromkeys(context['required_service_uptake'] + context['peer_sources'][:1]))
    return {'focus': {'source': key, 'quote': quote}, 'gap': 'Fixture conceptual gap',
            'action': 'hold', 'reason': 'Fixture leaves the gap unresolved', 'expected_change': None,
            'uptake': [{'source': k, 'quote': None, 'effect': 'unresolved',
                       'reason': 'Fixture cannot infer a conceptual connection', 'consequence': None}
                      for k in needed],
            'outcome': {'kind': 'unchanged', 'statement': 'Fixture reports no scientific progress',
                        'remaining_gap': 'Fixture conceptual gap'}}
