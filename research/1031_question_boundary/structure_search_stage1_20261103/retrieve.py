"""Bounded retrieval adapter; provenance and source scope are explicit."""
import json
from pathlib import Path
import urllib.parse
import urllib.request
import experiment as e

ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent

def main():
    cached=[]
    specs=[
        ('MDA','https://arxiv.org/abs/2608.09696',BASE/'model_variable_redesign_20261103/raw/mda.txt',205,245,'2026 preprint; model expansion after predictive failure'),
        ('BMD','https://arxiv.org/abs/2610.25747',BASE/'model_variable_redesign_20261103/raw/bmd.txt',365,398,'2026 preprint; residual/belief feedback and validated proposals'),
        ('LFF','https://doi.org/10.1007/s10994-020-05934-z',BASE/'literature_counterexample_20261101/raw/cegis_ml.txt',121,129,'Machine Learning 2021; generate-test-constrain with generalization/specialization pruning'),
        ('CEGIS-neighbors','https://doi.org/10.1007/s10994-020-05934-z',BASE/'literature_counterexample_20261101/raw/cegis_ml.txt',184,190,'Related-work descriptions of SMT properties and partial programs; secondary discussion, not independent implementation verification')]
    for name,url,p,lo,hi,scope in specs:
        lines=p.read_text().splitlines()
        cached.append(dict(id=name,url=url,source_path=str(p.relative_to(BASE)),source_sha256=e.sha(p),line_start=lo,line_end=hi,excerpt='\n'.join(lines[lo-1:hi]),scope=scope))
    e.write(ROOT/'retrieval/adapter_freeze.json',dict(time=e.now(),adapter_sha256=e.sha(Path(__file__)),cached_source_hashes={s['source_path']:s['source_sha256'] for s in cached},index_cap=2,full_request_cap=2))
    bundle=dict(stage='targeted retrieval planning',evidence=e.read(ROOT/'visible/evidence.json'),constraint=e.read(ROOT/'CONSTRAINT_AUDIT.json'),existing_source_excerpts=cached,instruction='Choose at most 2 concise English search queries for nearest evidence-to-search-constraint methods and mathematical state representation. Give source-grounded transferable structures and conditions, with an executable acquisition or test. Do not claim originality, source results not in excerpts, or a uniquely physical state. You cannot execute retrieval; broker will fetch exact queries.',output_schema=dict(queries=['two strings'],transfer_cards=[dict(source_id='one of source ids',structure='actual operation',assumptions='conditions',target_mapping='how it relates to this observation problem',quantity_acquisition='how any new quantity could be computed/measured, or not applicable',transfer_test='testable')],nearest_overlap='specific established operations',unresolved_originality='specific search gaps'))
    proposal=e.infer('01b_retrieval',bundle);e.write(ROOT/'retrieval/plan.json',proposal)
    queries=proposal.get('queries',[])[:2];requests=[];sources=[]
    for i,query in enumerate(queries):
        url='https://api.openalex.org/works?'+urllib.parse.urlencode(dict(search=query,per_page=5))
        req=dict(query=query,url=url,time=e.now());e.write(ROOT/f'retrieval/request_{i}.json',req)
        try:
            request=urllib.request.Request(url,headers={'User-Agent':'StructureSearchStage1/1.0'})
            with urllib.request.urlopen(request,timeout=25) as response:raw=response.read().decode()
            e.write(ROOT/f'retrieval/raw_{i}.json',raw)
            data=json.loads(raw)
            for row in data.get('results',[]):
                inv=row.get('abstract_inverted_index') or {};words={j:w for w,positions in inv.items() for j in positions}
                abstract=' '.join(words[j] for j in sorted(words))
                sources.append(dict(id=row['id'],title=row.get('title'),doi=row.get('doi'),date=row.get('publication_date'),abstract=abstract,query=query,scope='Index abstract and metadata; not full-text evidence of operations'))
            requests.append(dict(**req,status='returned',raw_sha256=e.sha(ROOT/f'retrieval/raw_{i}.json')))
        except Exception as exc:
            err=dict(**req,status='failed',error=str(exc));e.write(ROOT/f'retrieval/error_{i}.json',err);requests.append(err)
    url='https://www.jmlr.org/papers/v2/shalizi01a.html'
    req=dict(url=url,time=e.now(),purpose='Foundational causal-state representation abstract and article record')
    e.write(ROOT/'retrieval/state_source_request.json',req)
    try:
        with urllib.request.urlopen(url,timeout=25) as response:raw=response.read().decode()
        e.write(ROOT/'retrieval/shalizi01a.html',raw)
        requests.append(dict(**req,status='returned',raw_sha256=e.sha(ROOT/'retrieval/shalizi01a.html'),scope='Article page and abstract, not full paper'))
    except Exception as exc:
        e.write(ROOT/'retrieval/state_source_error.json',dict(**req,status='failed',error=str(exc)))
        requests.append(dict(**req,status='failed',error=str(exc)))
    e.write(ROOT/'retrieval/FETCH_LOG.json',requests)
    e.write(ROOT/'LITERATURE_BUNDLE.json',dict(cached_primary_excerpts=cached,retrieval_agent_plan=proposal,fresh_index_sources=sources,request_log=requests,scope='Targeted, non-exhaustive retrieval. Index retrieval or theoretical analogy is not validation on the target system. No correct target mechanism or evaluator-only source supplied.'))
    print(json.dumps(dict(queries=queries,returned_sources=len(sources),requests=[dict(url=r['url'],status=r['status']) for r in requests]),ensure_ascii=False))

if __name__=='__main__':main()
