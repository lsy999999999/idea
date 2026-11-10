"""Read-only source/data tools with explicit provenance and bounded results."""
from __future__ import annotations
import ast, hashlib, json, time
from pathlib import Path
import numpy as np
import pandas as pd


def clean(value):
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, np.ndarray):
        return clean(value.tolist())
    if isinstance(value, np.generic):
        return clean(value.item())
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def function(name, description, properties, required=None, strict=True):
    return {'type': 'function', 'function': {'name': name, 'description': description, 'strict': strict,
            'parameters': {'type': 'object', 'properties': properties, 'required': required or list(properties), 'additionalProperties': False}}}


READ = function('read_document', 'Read a supplied immutable document, including omitted context. JSON pointer selects a section; pagination never silently truncates. raw=true returns original text for quotations.', {
    'ref': {'type': 'string'}, 'pointer': {'type': 'string'}, 'offset': {'type': 'integer','minimum':0}, 'limit': {'type': 'integer','minimum':1,'maximum':12000}, 'raw': {'type': 'boolean'}})
READ_BATCH = function('read_documents', 'Read several needed documents in one call to avoid repeated model round-trips. Each page has explicit next_offset and SHA. Total requested characters must be at most 24000.', {
    'requests': {'type':'array','minItems':1,'maxItems':8,'items':{'type':'object','properties':READ['function']['parameters']['properties'],
    'required':READ['function']['parameters']['required'],'additionalProperties':False}}})
ANALYZE = function('analyze_csv', 'Compute on the ENTIRE registered CSV (not preview rows). Numeric column names are arrays. scan selections use group_column/group_value. Define variables in order and output safe array expressions. Functions: abs,sqrt,sin,cos,mean,sum,std,min,max,median,quantile,isfinite,where,clip,diff(axis=0),norm(axis=-1),shift,rolling. No Python execution or file access.', {
    'dataset': {'type': 'string'}, 'group_column': {'type': ['string', 'null']}, 'group_value': {'type': ['string', 'null']},
    'variables': {'type': 'array', 'items': {'type': 'object', 'properties': {'name': {'type': 'string'}, 'expression': {'type': 'string'}}, 'required': ['name','expression'], 'additionalProperties': False}},
    'outputs': {'type': 'array', 'items': {'type': 'object', 'properties': {'name': {'type': 'string'}, 'expression': {'type': 'string'}}, 'required': ['name','expression'], 'additionalProperties': False}}})
SEARCH = function('search_sources', 'Search actual public scientific indexes, save eligible readable sources and return IDs, access depth and excerpts. Search success is not evidence of relevance or understanding.', {'queries': {'type': 'array','minItems':1,'maxItems':2,'items': {'type': 'string','minLength':1,'maxLength':400}}})


class ResearchTools:
    def __init__(self, store, workspace, datasets, broker=None, expression=None, max_calls=64, max_searches=4, source_policy=None):
        self.store, self.workspace = store, Path(workspace)
        self.directory = self.workspace/'tools'; self.directory.mkdir(parents=True, exist_ok=True)
        self.datasets = {name: Path(p).resolve() for name,p in datasets.items()}
        self.hashes = {n: hashlib.sha256(p.read_bytes()).hexdigest() for n,p in self.datasets.items()}
        self.broker, self.expression = broker, expression
        self.source_policy=source_policy or (broker.policy if broker else None)
        self.max_calls, self.max_searches = max_calls, max_searches
        self.calls, self.searches = 0, 0
        self.events = []

    @property
    def definitions(self):
        return [READ, READ_BATCH] + ([ANALYZE] if self.datasets else []) + ([SEARCH] if self.broker else [])

    def catalog(self):
        return [{'id': name, 'sha256': self.hashes[name], 'rows': len(pd.read_csv(path)),
                 'columns': list(pd.read_csv(path, nrows=0).columns), 'access': 'full_csv_via_analyze_csv'} for name,path in self.datasets.items()]

    def call(self, name, args, call_id):
        cache_key = hashlib.sha256(json.dumps({'name':name,'args':args},sort_keys=True).encode()).hexdigest()
        cache = self.directory/(cache_key+'.json')
        if cache.exists():
            saved=json.loads(cache.read_text())
            if self.source_policy and self.source_policy.config.get('historical_case'):
                if saved.get('policy_fingerprint')!=self.source_policy.fingerprint:
                    raise ValueError('Cached tool policy changed; use a clean historical run')
            if name=='search_sources':
                if not self.broker:raise ValueError('Search is disabled, including cached search replies')
                for row in saved['result'].get('sources',[]):
                    source=self.broker.sources.get(row['id'])
                    if source is None or self.broker.policy.rejection(source):
                        raise ValueError('Cached search source violates the current policy')
                    if row.get('excerpt')!=source['text'][:1800]:
                        raise ValueError('Cached search excerpt differs from its screened source')
            # Reinstall returned documents after process restart, without repeating the tool.
            for path in saved.get('registered_paths', []):
                self.store.add_file(path)
            self.events.append({'call_id':call_id,'name':name,'cached':True,'artifact':str(cache)})
            ref=self.store.add_file(cache)
            return {**saved['result'],'tool_record_ref':ref,'tool_record_path':str(cache)}
        previous = list(self.directory.glob('*.json'))
        if len(previous) >= self.max_calls:
            return {'status':'tool_budget_exhausted','message':'Preserve unresolved work and submit the current result.'}
        self.calls += 1; start=time.monotonic(); registered=[]
        try:
            if name == 'read_document':
                result=self.store.read(**args)
            elif name == 'read_documents':
                requests=args['requests']
                if not isinstance(requests,list) or not 1<=len(requests)<=8 or any(type(r.get('limit')) is not int or r['limit']<1 for r in requests):
                    raise ValueError('Batch requires 1-8 document pages, with positive limits totaling at most 24000 characters')
                remaining=24000;pages=[]
                for i,page in enumerate(requests):
                    chosen=min(page['limit'],12000,max(1,remaining//(len(requests)-i)))
                    pages.append(self.store.read(**{**page,'limit':chosen}));remaining-=chosen
                result={'status':'read','documents':pages,'paging':'Large batches are paginated automatically; follow next_offset for remaining text.'}
            elif name == 'analyze_csv':
                result=self.analyze(**args)
            elif name == 'search_sources' and self.broker:
                searches=sum(json.loads(p.read_text()).get('name')=='search_sources' for p in previous)
                if searches>=self.max_searches:
                    raise ValueError('Search budget exhausted; read returned sources or preserve the unresolved gap')
                queries=args['queries']
                if not isinstance(queries,list) or not 1<=len(queries)<=2 or any(not isinstance(q,str) or not 1<=len(q)<=400 for q in queries):
                    raise ValueError('Supply 1-2 queries, each at most 400 characters')
                reply=self.broker.search({'queries':queries},'tool_'+cache_key[:16])
                sources=[]
                for s in reply['sources']:
                    path=self.broker.root/'accepted'/(s['id']+'.json')
                    ref=self.store.add_file(path);registered.append(str(path))
                    sources.append({**{k:s.get(k) for k in ['id','title','url','date','access']},'ref':ref,'local_path':str(path),'excerpt':s['text'][:1800],
                                    'excerpt_truncated':len(s['text'])>1800})
                result={'status':reply['status'],'sources':sources,'attempts':reply['attempts'],'remaining_gap':reply['remaining_gap']}
            else:
                raise ValueError('Unknown or disabled tool')
            result=clean(result)
        except Exception as exc:
            result={'status':'error','error_type':type(exc).__name__,'message':str(exc)}
        # The model sees a bounded reply. Complete arrays/records remain in the artifact.
        record={'name':name,'args':args,'call_id':call_id,'seconds':time.monotonic()-start,'registered_paths':registered,'result':result,
                'policy_fingerprint':self.source_policy.fingerprint if self.source_policy else None}
        cache.write_text(json.dumps(record,ensure_ascii=False,indent=2,allow_nan=False))
        ref=self.store.add_file(cache);self.store.save()
        self.events.append({'call_id':call_id,'name':name,'cached':False,'artifact':str(cache)})
        return {**result,'tool_record_ref':ref,'tool_record_path':str(cache)}

    def analyze(self, dataset, group_column=None, group_value=None, variables=None, outputs=None):
        if dataset not in self.datasets:
            raise ValueError('Unknown dataset; use the dataset catalog')
        path=self.datasets[dataset]
        if hashlib.sha256(path.read_bytes()).hexdigest()!=self.hashes[dataset]:
            raise ValueError('Dataset changed after stage initialization')
        if path.stat().st_size>20_000_000:
            raise ValueError('CSV byte budget exceeded')
        frame=pd.read_csv(path)
        if len(frame)>200_000:
            raise ValueError('CSV row budget exceeded')
        original_rows=len(frame)
        if (group_column is None)!=(group_value is None):
            raise ValueError('Provide both group_column and group_value, or neither')
        if group_column is not None:
            if group_column not in frame:
                raise ValueError('Unknown group column')
            frame=frame.loc[frame[group_column].astype(str)==str(group_value)]
        if not len(frame):
            raise ValueError('Selection has no rows')
        env={n:frame[n].to_numpy(dtype=float) for n in frame.select_dtypes('number') if n.isidentifier() and not n.startswith('_')}
        def evaluate(text):
            if not isinstance(text,str) or len(text)>1200:
                raise ValueError('Expression text budget exceeded')
            tree=ast.parse(text,mode='eval')
            for node in ast.walk(tree):
                # Prevent Python sequence repetition and giant scalar exponent towers.
                if isinstance(node,(ast.List,ast.Tuple,ast.Dict,ast.Set)):
                    raise ValueError('Use column arrays and scalar expressions, not Python collection literals')
                if isinstance(node,ast.Constant) and isinstance(node.value,(int,float)) and abs(node.value)>1e9:
                    raise ValueError('Scalar literal budget exceeded')
                if isinstance(node,ast.BinOp) and isinstance(node.op,ast.Pow) and any(isinstance(x,ast.BinOp) and isinstance(x.op,ast.Pow) for x in ast.walk(node.left)):
                    raise ValueError('Nested scalar powers are not supported')
                if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='diff':
                    n=next((k.value for k in node.keywords if k.arg=='n'),node.args[1] if len(node.args)>1 else ast.Constant(1))
                    if not isinstance(n,ast.Constant) or type(n.value) is not int or not 0<=n.value<=20:
                        raise ValueError('diff order must be a literal integer in 0..20')
            value=np.asarray(self.expression(text,env))
            if value.dtype.kind not in 'biuf' or value.size>2_000_000:
                raise ValueError('Numeric intermediate budget exceeded')
            return value
        variables,outputs=variables or [],outputs or []
        if len(variables)>12 or not 1<=len(outputs)<=12:
            raise ValueError('At most 12 variables and 1-12 outputs')
        for item in variables:
            name=item['name']
            if not isinstance(name,str) or not name.isidentifier() or name.startswith('_') or name in env:
                raise ValueError('Use a new safe variable name')
            env[name]=evaluate(item['expression'])
        result={}
        for item in outputs:
            name=item['name']
            if not isinstance(name,str) or not name or name in result:
                raise ValueError('Output names must be nonempty and unique')
            value=evaluate(item['expression'])
            if value.size>10000 or value.dtype.kind not in 'biuf':
                raise ValueError('Numeric output budget exceeded; request a reduction')
            result[name]={'shape':list(value.shape),'value':clean(value),'nonfinite_count':int((~np.isfinite(value)).sum())}
        full={'status':'executed','dataset':dataset,'sha256':self.hashes[dataset],
              'total_rows':original_rows,'selected_rows':len(frame),'selection':{'column':group_column,'value':group_value},'outputs':result,
              'scope':'Executed researcher-authored expressions on registered measurements; not validation of causal interpretation.'}
        # Full values are saved separately; previews are explicitly marked and readable by ref.
        for item in result.values():
            if np.prod(item['shape'])>32:
                content=json.dumps(item,ensure_ascii=False,allow_nan=False)
                ref=self.store.add('array:'+hashlib.sha256(content.encode()).hexdigest(),content)
                item.update(value_preview=np.asarray(item.pop('value'),dtype=object).flatten()[:12].tolist(),full_value_ref=ref,truncated=True)
        return full
