from pathlib import Path
import json
import math
from collections import Counter,defaultdict
import numpy as np
import requests

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT.parent/'sources/code/researchagent/data'
d=json.loads((ROOT/'battery_s2.json').read_text())
refs=[r for r in d['references'] if r.get('abstract')]
ids=[d['corpusId']]+[r['corpusId'] for r in refs]
note=''
try:
    r=requests.post('https://api.semanticscholar.org/graph/v1/paper/batch',
                    params={'fields':'corpusId,embedding.specter_v2'},
                    json={'ids':['CorpusId:'+str(i) for i in ids]},timeout=25)
    (ROOT/'s2_embeddings.json').write_text(json.dumps({'status':r.status_code,'body':r.json()}))
    r.raise_for_status()
    vectors={x['corpusId']:np.asarray(x['embedding']['vector']) for x in r.json() if x and x.get('embedding')}
    v=vectors[d['corpusId']]
    refs=sorted([x for x in refs if x['corpusId'] in vectors],key=lambda x:np.dot(v,vectors[x['corpusId']])/(np.linalg.norm(v)*np.linalg.norm(vectors[x['corpusId']])),reverse=True)[:10]
    note='Semantic Scholar specter_v2 cosine ranking, NumPy implementation of upstream ranking.'
except Exception as exc:
    refs=sorted(refs,key=lambda r:sum(t in r['title'].lower() for t in ['impedance','health','battery','batteries','aging']),reverse=True)[:10]
    note='Embedding service unavailable; transparent lexical title ranking fallback: '+type(exc).__name__
knowledge=[json.loads(line) for line in (SOURCE/'knowledge.jsonl').open()]
p2e={x['corpusid']:x['knowledge'] for x in knowledge}
ec=Counter();co=defaultdict(Counter)
for x in knowledge:
    es=x['knowledge'];ec.update(es)
    for k in es:co[k].update({a:b for a,b in es.items() if a!=k})
pe=sum((Counter(p2e.get(i,{})) for i in [d['corpusId']]+[r['corpusId'] for r in refs]),start=Counter())
pe=list(pe.elements());cands=sum((co[e] for e in pe),start=Counter())
def score(e):
    return sum(math.log2((co[e][p]+1e-16)/(sum(co[e].values())+1e-16)) for p in pe)+math.log2(ec[e]/sum(ec.values())+1e-16)
entities=sorted([e for e,c in cands.items() if c>=3],key=score,reverse=True)[:30]
context={'paper':{'title':d['title'],'abstract':d['abstract']},'references':refs,'entities':entities}
(ROOT/'case_context.json').write_text(json.dumps(context,ensure_ascii=False,indent=2))
(ROOT/'case_provenance.json').write_text(json.dumps({'source_paper_doi':'10.1186/s41601-023-00314-w','original_repository_corpus_id':d['corpusId'],'raw_source':'battery_s2.json','reference_selection':note,'references':len(refs),'entities':len(entities),'raw_battery_measurements_used':False,'knowledge_ranking':'Unchanged co-occurrence log likelihood formula; sorted replaces torch.topk.'},indent=2))
print(note,'references',len(refs),'entities',len(entities))
