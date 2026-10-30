"""Reproducible offline baselines; no LLM inference or external network calls."""
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
import hashlib
import json
import math
import random
import re
import statistics
import time

ROOT = Path(__file__).resolve().parent
DATA = ROOT.parent/'2026-10-30_data_feasibility'/'samples'
OUT = ROOT/'results'
CUTOFF = '2026-10-30'
SEED = 20261030
BUDGETS = [1,3,5,8,12]
STOP = set('a an the of in on at for to and or is are was were be been being what which how much many did does do with from by as it its this that these those than then there their per during ended end year years total company million millions billion billions'.split())

def save(name, obj):
    (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2))

def eq(a,b):
    return math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-12)

def row_order(r):
    return (r['filed'],r['accn'])

def ambiguous_same_day(rows):
    by_date=defaultdict(set)
    for r in rows:by_date[r['filed']].add(r['val'])
    return any(len(values)>1 for values in by_date.values())

def select(rows, cutoff, method):
    if method=='earliest': return min(rows,key=row_order)
    if method=='latest': return max(rows,key=row_order)
    if method=='mode':
        # One vote per distinct accession/value, not repeated frame metadata.
        votes=Counter(v for _,v in {(r['accn'],r['val']) for r in rows})
        maximum=max(votes.values())
        return max((r for r in rows if votes[r['val']]==maximum),key=row_order)
    if method=='cutoff_rule':
        visible=[r for r in rows if r['filed']<=cutoff]
        return max(visible,key=row_order) if visible else None
    raise ValueError(method)

def sec_groups():
    groups={};excluded=Counter();input_counts={}
    for company in ['apple','microsoft']:
        obj=json.loads((DATA/f'sec_{company}_facts.json').read_text())
        local=defaultdict(list)
        for tag,f in obj['facts']['us-gaap'].items():
            for unit,rows in f['units'].items():
                for r in rows:
                    if r['form'] not in ('10-K','10-K/A') or r['filed']>CUTOFF:continue
                    if r.get('start'):
                        span=(date.fromisoformat(r['end'])-date.fromisoformat(r['start'])).days
                        if not 300<=span<=400:
                            excluded['quarterly_or_other_duration_records']+=1;continue
                    local[(company,tag,unit,r.get('start'),r['end'])].append(r)
        input_counts[company]=len(local)
        for key,rows in local.items():
            by_date=defaultdict(set)
            for r in rows:by_date[r['filed']].add(r['val'])
            if len(by_date)<2:
                excluded['single_filing_date_groups']+=1;continue
            if ambiguous_same_day(rows):
                excluded['ambiguous_same_day_groups']+=1;continue
            unique={tuple(sorted(r.items())):r for r in rows}
            groups[key]=sorted(unique.values(),key=row_order)
    return groups,dict(excluded),input_counts

def temporal_experiment():
    groups,excluded,input_counts=sec_groups()
    counts=defaultdict(lambda:Counter(n=0,value=0,citation=0,joint=0))
    queries=[];failures=[];group_summary=Counter()
    for key,rows in sorted(groups.items(),key=lambda x:repr(x[0])):
        company,tag,unit,start,end=key
        dates=sorted({r['filed'] for r in rows})
        checkpoints=sorted({dates[0],dates[len(dates)//2],CUTOFF})
        changed=len({r['val'] for r in rows})>1
        group_summary[f'{company}_eligible']+=1
        group_summary[f'{company}_changed']+=changed
        # Chronological replay generates target states; no retrieval method is called.
        cursor=0;state=None
        for cutoff in checkpoints:
            while cursor<len(rows) and rows[cursor]['filed']<=cutoff:
                state=rows[cursor];cursor+=1
            assert state is not None
            query_id=hashlib.sha256(repr((key,cutoff)).encode()).hexdigest()[:16]
            q=dict(id=query_id,company=company,tag=tag,unit=unit,start=start,end=end,cutoff=cutoff,
                   changed_group=changed,reference={'val':state['val'],'filed':state['filed'],'accn':state['accn']},predictions={})
            for method in ['earliest','latest','mode','cutoff_rule']:
                r=select(rows,cutoff,method)
                value=r is not None and eq(r['val'],state['val'])
                citation=r is not None and r['filed']<=cutoff
                joint=value and citation
                q['predictions'][method]={'val':r['val'],'filed':r['filed'],'accn':r['accn'],
                                          'value_correct':value,'citation_valid':citation,'joint_correct':joint}
                for category in ['all',company,'changed' if changed else 'unchanged']:
                    c=counts[(category,method)];c.update(n=1,value=int(value),citation=int(citation),joint=int(joint))
            queries.append(q)
            if not q['predictions']['latest']['value_correct'] and len(failures)<30:failures.append(q)
    with (OUT/'temporal_predictions.jsonl').open('w') as f:
        for q in queries:f.write(json.dumps(q,ensure_ascii=False)+'\n')
    metrics={}
    for (category,method),c in counts.items():
        metrics.setdefault(category,{})[method]={**dict(c),**{k+'_rate':c[k]/c['n'] for k in ['value','citation','joint']}}
    result={'eligible_groups':len(groups),'group_summary':dict(group_summary),'queries':len(queries),
            'eligible_group_count_before_multifiling_filter':input_counts,'exclusions':excluded,'metrics':metrics}
    save('temporal_results.json',result);save('temporal_failure_examples.json',failures)
    return result,groups

def tokenize(text):
    tokens=re.findall(r'[a-z]+|\d+(?:\.\d+)?',text.lower().replace(',',''))
    return [x[:-1] if len(x)>4 and x.endswith('s') else x for x in tokens if x not in STOP]

def build_corpus(example):
    corpus={f'text_{i}':t for i,t in enumerate(example['pre_text']+example['post_text']) if t.strip()}
    table=example['table']
    for i,row in enumerate(table):
        if i==0:txt=' | '.join(map(str,row))
        else:
            label=str(row[0]) if row else ''
            cells=[f'{table[0][j] if j<len(table[0]) else "column"}: {value}' for j,value in enumerate(row[1:],1)]
            txt=label+' | '+' | '.join(cells)
        corpus[f'table_{i}']=txt
    return corpus

class BM25:
    def __init__(self,corpus):
        self.ids=list(corpus);self.tokens=[tokenize(corpus[k]) for k in self.ids]
        self.tfs=[Counter(t) for t in self.tokens];self.lengths=[len(t) for t in self.tokens]
        self.avg=statistics.mean(self.lengths) or 1
        df=Counter(t for doc in self.tfs for t in doc)
        self.idf={t:math.log(1+(len(self.ids)-n+0.5)/(n+0.5)) for t,n in df.items()}
    def scores(self,query):
        scores=[]
        for tf,dl in zip(self.tfs,self.lengths):
            value=0.
            for t in set(query):
                f=tf.get(t,0)
                if f:value+=self.idf[t]*f*2.5/(f+1.5*(0.25+0.75*dl/self.avg))
            scores.append(value)
        return scores
    def order(self,scores):
        return sorted(range(len(self.ids)),key=lambda i:(-scores[i],self.ids[i]))
    def rank(self,question,feedback=False):
        query=tokenize(question);scores=self.scores(query)
        if feedback:
            top=self.order(scores)[0];tf=self.tfs[top]
            extras=sorted((t for t in tf if t not in query and not t[0].isdigit()),key=lambda t:(-tf[t]*self.idf[t],t))[:6]
            extra_scores=self.scores(extras)
            scores=[a+0.30*b for a,b in zip(scores,extra_scores)]
        return [self.ids[i] for i in self.order(scores)]

def retrieval_experiment():
    data=json.loads((DATA/'finqa_dev.json').read_text())
    metrics=defaultdict(lambda:Counter(n=0,recall_sum=0.,complete=0,words=0,chunks=0))
    output=[];missing=[];hist=Counter();page_ids=set();failure_examples=[]
    paired=Counter(improved=0,worsened=0,unchanged=0)
    for ex in data:
        corpus=build_corpus(ex);index=BM25(corpus)
        # Predict before accessing any answer-side fields.
        ranks={'bm25':index.rank(ex['qa']['question']),'bm25_feedback':index.rank(ex['qa']['question'],True)}
        seed=SEED+int(hashlib.sha256(ex['id'].encode()).hexdigest()[:8],16)
        random_order=list(corpus);random.Random(seed).shuffle(random_order);ranks['random']=random_order
        gold=set(ex['qa']['gold_inds']);page_ids.add(ex['filename']);hist[len(gold)]+=1
        if not gold or not gold.issubset(corpus):
            missing.append({'id':ex['id'],'missing_ids':sorted(gold-set(corpus)),'empty_gold':not gold});continue
        row={'id':ex['id'],'source_page':ex['filename'],'question':ex['qa']['question'],
             'gold_ids':sorted(gold),'gold_count':len(gold),'corpus_chunks':len(corpus),'predictions':{}}
        for method,ranking in ranks.items():
            row['predictions'][method]={}
            for k in BUDGETS:
                chosen=ranking[:k];recall=len(gold.intersection(chosen))/len(gold);complete=gold.issubset(chosen)
                words=sum(len(corpus[c].split()) for c in chosen)
                row['predictions'][method][str(k)]={'ids':chosen,'recall':recall,'complete':complete,'words':words}
                for category in ['all','single' if len(gold)==1 else 'multiple']:
                    metrics[(category,method,k)].update(n=1,recall_sum=recall,complete=int(complete),words=words,chunks=len(chosen))
        a=row['predictions']['bm25']['5']['complete'];b=row['predictions']['bm25_feedback']['5']['complete']
        paired['improved' if b and not a else 'worsened' if a and not b else 'unchanged']+=1
        if not a and len(failure_examples)<20:
            failure_examples.append({**row,'gold_text':{k:corpus[k] for k in sorted(gold)},
                                     'bm25_top5_text':{k:corpus[k] for k in ranks['bm25'][:5]}})
        output.append(row)
    aggregates={}
    for (category,method,k),c in metrics.items():
        aggregates.setdefault(category,{}).setdefault(method,{})[str(k)]={
            'n':c['n'],'complete_count':c['complete'],'complete_rate':c['complete']/c['n'],
            'macro_recall':c['recall_sum']/c['n'],'average_words':c['words']/c['n'],'average_chunks':c['chunks']/c['n']}
    result={'input_questions':len(data),'scored_questions':len(output),'unique_source_pages':len(page_ids),
            'missing_gold_ids':missing,'gold_count_histogram':dict(hist),'metrics':aggregates,
            'feedback_vs_bm25_at5':dict(paired)}
    with (OUT/'retrieval_predictions.jsonl').open('w') as f:
        for row in output:f.write(json.dumps(row,ensure_ascii=False)+'\n')
    save('retrieval_results.json',result);save('retrieval_failure_examples.json',failure_examples)
    return result

def split_diagnostic(groups):
    matches=[]
    allowed={'EarningsPerShareBasic','EarningsPerShareDiluted','CommonStockDividendsPerShareDeclared'}
    for key,rows in groups.items():
        company,tag,unit,start,end=key
        if company!='apple' or tag not in allowed or unit!='USD/shares' or end>='2020-08-31':continue
        before=[r for r in rows if r['filed']<'2020-08-31'];after=[r for r in rows if r['filed']>='2020-08-31']
        if not before or not after:continue
        old=max(before,key=row_order);new=min(after,key=row_order)
        if old['val']!=new['val'] and abs(old['val']/4-new['val'])<=0.011:
            matches.append({'tag':tag,'start':start,'end':end,'old':old,'new':new,'status':'split_compatible_not_independently_adjudicated'})
    result={'candidate_count':len(matches),'candidates':matches,
            'source_announcement':'https://www.apple.com/newsroom/2020/07/apple-reports-third-quarter-results/',
            'limitation':'Numerical compatibility and a public announcement do not replace the filing accounting note.'}
    save('split_diagnostic.json',result);return result

def full_context_diagnostic():
    # Added after the initial run: this is a diagnostic, not a frozen primary endpoint.
    data=json.loads((DATA/'finqa_dev.json').read_text())
    lengths=[];covered=0
    for ex in data:
        corpus=build_corpus(ex)
        lengths.append(sum(len(t.split()) for t in corpus.values()))
        covered+=bool(ex['qa']['gold_inds']) and set(ex['qa']['gold_inds']).issubset(corpus)
    lengths.sort()
    result={'n':len(lengths),'average_words':statistics.mean(lengths),
            'median_words':statistics.median(lengths),'p95_words':lengths[math.ceil(.95*len(lengths))-1],
            'max_words':max(lengths),'fraction_under_2000_words':sum(n<=2000 for n in lengths)/len(lengths),
            'fraction_under_4000_words':sum(n<=4000 for n in lengths)/len(lengths),
            'annotated_evidence_coverage_if_entire_provided_context_returned':covered/len(lengths),
            'note':'Post-hoc context-size diagnostic; no LLM answer accuracy measured. Full supplied context is not the entire original annual report.'}
    save('full_context_diagnostic.json',result)

def verify_core():
    rows=[{'filed':'2019-01-01','accn':'a','val':10},{'filed':'2020-01-01','accn':'b','val':20}]
    assert select(rows,'2018-12-31','cutoff_rule') is None
    assert select(rows,'2019-01-01','cutoff_rule')['val']==10
    assert select(rows,'2019-12-31','cutoff_rule')['val']==10
    assert select(rows,'2020-01-01','cutoff_rule')['val']==20
    stable=[{**r,'val':10} for r in rows]
    chosen=select(stable,'2019-06-01','latest')
    assert chosen['val']==10 and chosen['filed']>'2019-06-01'
    assert ambiguous_same_day([rows[0],{**rows[0],'accn':'c','val':11}])
    assert not ambiguous_same_day([rows[0],{**rows[0],'accn':'c'}])
    sample={'pre_text':['before'],'post_text':['after'],'table':[['metric','2019'],['cash','7']],
            'qa':{'gold_inds':{'text_0':'SECRET_EVIDENCE'},'answer':'SECRET_ANSWER'}}
    corpus=build_corpus(sample)
    assert corpus['text_1']=='after' and '2019' in corpus['table_1']
    assert all('SECRET' not in text for text in corpus.values())

def main():
    OUT.mkdir(parents=True,exist_ok=True);verify_core();started=time.perf_counter()
    provenance={name:hashlib.sha256((DATA/name).read_bytes()).hexdigest() for name in
                ['sec_apple_facts.json','sec_microsoft_facts.json','finqa_dev.json','apple_split_release.html']}
    temporal,groups=temporal_experiment();retrieval=retrieval_experiment();split=split_diagnostic(groups)
    full_context_diagnostic()
    save('run_manifest.json',{'date':CUTOFF,'seed':SEED,'input_sha256':provenance,
         'protocol_sha256':hashlib.sha256((ROOT/'PROTOCOL.md').read_bytes()).hexdigest(),
         'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
         'elapsed_seconds':time.perf_counter()-started,'llm_inference_run':False,
         'tests':'temporal boundary, future citation with equal value, ambiguous same-day values, evidence-label separation'})
    print(json.dumps({'temporal':temporal,'retrieval':retrieval,'split_candidate_count':split['candidate_count']},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
