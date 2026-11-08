"""Controller recovery: execute the researchers' own pending learning queries."""
import json
from pathlib import Path
import sys
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
sys.path.insert(0, str(PROJECT / 'historical_inquiry'))
from knowledge_broker import KnowledgeBroker, SourcePolicy

def fetch(url):
    with urlopen(Request(url, headers={'User-Agent': 'ScientificInquiryEvaluation/1.0'}), timeout=12) as r:
        return r.read(4_000_000).decode('utf-8')

config = {'knowledge_before_exclusive': '2026-11-07', 'excluded_dois': [],
          'excluded_titles': [], 'retrieval_results_per_query': 3, 'read_full_text': True}
broker = KnowledgeBroker(ROOT / 'requested_retrieval', SourcePolicy(config), fetch)
run = PROJECT / 'runs/e2e_eval_20261106_wine'
queries = []
requests = []
for i in (0, 1):
    p = run / f'stages/03_exchange_{i}/native-001/workspace/result.json'
    request = json.loads(p.read_text())['learning_request']
    requests.append({'source': str(p), 'request': request})
    # Two short researcher-authored queries; no new scientific agenda supplied.
    q = request['search_terms'][1 if i == 0 else 0]
    if q not in queries:
        queries.append(q)
result = broker.search({'queries': queries}, 'actual_requested_learning')
(ROOT / 'REQUESTED_LEARNING_REPLY.json').write_text(json.dumps(
    {'controller_recovery': True, 'original_requests': requests, 'reply': result},
    ensure_ascii=False, indent=2))
print(json.dumps({'queries': queries, 'sources': len(result['sources']),
                  'attempts': result['attempts']}, ensure_ascii=False))
