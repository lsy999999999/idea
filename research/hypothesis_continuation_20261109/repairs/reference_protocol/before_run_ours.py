"""Native inquiry controller with compact, tool-capable, provider-neutral transport."""
from __future__ import annotations
import argparse, difflib, hashlib, shutil, json, os, sys, time, traceback
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlparse
import requests
from openai import OpenAI
from research_context import ContextStore, dumps
from research_tools import ResearchTools, function
from flexible_locator import select
from submission_repair import apply_edits, save_draft, load_draft, repair_context

ROOT=Path(__file__).resolve().parents[1]
PROJECT=Path(__file__).resolve().parent/'ours_source'
sys.path.insert(0,str(PROJECT/'src'))
import learning_lab as lab
from learning_memory import Memory, validate_notes
from discover import read, write
from learning_support import QuestionState, HypothesisState, validate_uptake, audit_review, material_coverage, service_request, validate_memory_use, expand_review_packet
from hypothesis_cycle import validate_step, anchored, texts
from analysis_executor import expression
from knowledge_broker import KnowledgeBroker, SourcePolicy
from case_access import locked_policy, assert_measurements, screen_document, actor_brief

VERSION='tool-transport-v8-flexible-locators'
SUBMIT=function('submit_result','Submit a stage result once. If validation fails it is saved as a draft; use patch_result to change only affected fields.',
                {'result':{'type':'object','additionalProperties':True}},strict=False)


PATCH=function('patch_result','Repair the latest saved draft using only changed fields. Unmentioned content is preserved. No state is committed until all validation passes.',
    {'draft_ref':{'type':'string'},'edits':{'type':'array','minItems':1,'maxItems':24,
     'items':{'type':'object','properties':{'op':{'type':'string','enum':['set','remove']},
     'path':{'type':'string','description':'Non-root JSON pointer, e.g. /summary or /claims/0/text'},
     'value':{}},'required':['op','path'],'additionalProperties':False}}},strict=False)


class GenerationFrozen(Exception):
    pass


class PublicFetcher:
    """Only broker-owned public indexes. No arbitrary URLs, credentials or private hosts."""
    hosts={'www.ebi.ac.uk','api.crossref.org','api.openalex.org'}
    def __init__(self,path,limit=240):
        self.path=Path(path);self.limit=limit
    def __call__(self,url):
        parsed=urlparse(url)
        if parsed.scheme!='https' or parsed.hostname not in self.hosts or parsed.username or parsed.password:
            raise ValueError('Only the configured public scientific indexes are readable')
        records=read(self.path) if self.path.exists() else []
        if len(records)>=self.limit:
            raise ValueError('Run retrieval request budget exhausted')
        item={'url':url,'status':'started'};records.append(item);write(self.path,records)
        try:
            with requests.get(url,headers={'User-Agent':'ResearchInquiry/3.1 (public scientific source reading)'},timeout=(5,12),allow_redirects=False,stream=True) as response:
                response.raise_for_status()
                if 300<=response.status_code<400:
                    raise ValueError('Unexpected redirect from public index')
                pieces=[];size=0
                for part in response.iter_content(65536):
                    size+=len(part)
                    if size>4_000_000:raise ValueError('Source byte limit exceeded')
                    pieces.append(part)
                body=b''.join(pieces).decode('utf-8')
            item.update(status='read',bytes=size,sha256=hashlib.sha256(body.encode()).hexdigest())
            return body
        except Exception as exc:
            item.update(status='failed',error_type=type(exc).__name__)
            raise
        finally:
            write(self.path,records)


class StageAdapter:
    def __init__(self,root,case,phase,cfg,knowledge='online',api=None):
        self.root,self.case,self.phase,self.cfg=Path(root),case,phase,cfg
        self.out=self.root/'runs'/case/'ours'/phase
        self.out.mkdir(parents=True,exist_ok=True)
        if (self.out/'FINAL_FREEZE.json').exists():raise ValueError('Frozen run; create a clean replay folder')
        self.run=PROJECT/'runs'/('hypothesis_flexible_'+case+'_'+phase)
        # Memory initializes its directory; keep it outside the native controller's new run.
        self.memory=Memory(PROJECT/'api_researchers'/case/('flexible_'+phase))
        self.domains=[('domain_scientist','光学偏振与光计算' if case=='optical' else '主动机械超材料与非平衡动力学'),('theory_scientist','统计物理、随机过程与可辨识性')]
        self.owners=[x[0] for x in self.domains]
        self.knowledge=knowledge
        self.fetch=PublicFetcher(self.run/'public_fetches.json')
        self.policy=locked_policy(case,{'retrieval_results_per_query':2,'read_full_text':True})
        self.source_policy=SourcePolicy(self.policy)
        if api is None:
            endpoint=read(self.root/'gateway_endpoint.json')['base_url']
            api=OpenAI(base_url=endpoint,api_key=f'{case}/ours/{phase}',max_retries=0,timeout=240)
        self.api=api

    def is_memory_probe(self,sid):
        return sid=='08_fresh_continuation' and self.cfg.get('continuation_mode','full_context')=='memory_only_probe'

    def broker(self,workspace):
        return KnowledgeBroker(workspace/'knowledge',SourcePolicy(self.policy),self.fetch) if self.knowledge=='online' else None

    def admit_document(self,path,text):
        if not str(path).startswith('array:'):
            p=Path(path).resolve()
            if not p.is_relative_to(self.root.resolve()) or 'controller_only' in p.parts:
                raise ValueError('Historical input must belong to this clean run, outside controller-only records')
        screen_document(self.source_policy,text)

    @staticmethod
    def parse(text):
        text=text.strip()
        if text.startswith('```'):text=text.split('\n',1)[1].rsplit('```',1)[0]
        value=json.loads(text)
        if not isinstance(value,dict):raise ValueError('Result must be a JSON object')
        return value

    def normalize(self,result,bindings,store):
        result=json.loads(json.dumps(result,ensure_ascii=False));changes=[]
        allowed=set(bindings.values())
        def source(value):
            if value in bindings:return bindings[value]
            if value in allowed:return value
            ref=store.resolve(value)
            matches=sorted(set(store.documents[ref]['paths'])&allowed)
            if len(matches)!=1:raise ValueError('Use an exact S-number from source_bindings; this document has multiple or no cycle aliases')
            return matches[0]
        step=result.get('development_step')
        if isinstance(step,dict):
            for row in [step.get('focus',{}),*step.get('uptake',[])]:
                if 'source' in row:
                    old=row['source'];row['source']=source(old)
                    if old!=row['source']:changes.append({'field':'development source','from':old,'to':row['source']})
                    original=store.documents[store.resolve(row['source'])]['text']
                    pointer=row.get('quote_pointer')
                    if pointer is not None:
                        if not isinstance(pointer,str):
                            raise ValueError('quote_pointer must locate a source string by path or unique field name')
                        value,canonical=select(json.loads(original),pointer)
                        row['quote_pointer']=canonical
                        if not isinstance(value,str) or not value.strip():
                            raise ValueError('quote_pointer must select a nonempty source string')
                        if row.get('quote') is not None and row['quote']!=value:
                            raise ValueError('quote conflicts with the exact quote_pointer value; omit the duplicate quote or supply the identical value')
                        row['quote']=value
                        changes.append({'field':'development quote','rule':'Resolve author-selected JSON pointer to exact source string','source':row['source'],'pointer':pointer})
                    quote=row.get('quote')
                    if quote is not None and not anchored(quote,original):
                        candidates=list(dict.fromkeys(t for t in texts(original) if 0<len(t)<=1200))
                        close=difflib.get_close_matches(quote,candidates,n=2,cutoff=.4) if isinstance(quote,str) else []
                        raise ValueError('Development quote is absent from '+str(old)+'. Quote an exact source string value, not a field-name plus its value. '
                                         'You may use quote_pointer to select the exact JSON string. Closest source strings (suggestions only): '+dumps(close))
            req=result.get('learning_request')
            if isinstance(req,dict) and req.get('context_ref')=='development_step':
                # The author chooses a structural reference; do not reconcile different prose silently.
                if ('gap' in req and req['gap']!=step['gap']) or ('why_now' in req and req['why_now']!=step['reason']):
                    raise ValueError('context_ref conflicts with explicit gap/why_now; omit the duplicated fields or make them identical')
                req['gap'],req['why_now']=step['gap'],step['reason']
                changes.append({'field':'learning_request','rule':'Resolve author-specified development_step reference'})
        for row in result.get('sources',[]):
            locator=row.get('local_path')
            if locator in store.documents:
                paths=[p for p in store.documents[locator]['paths'] if Path(p).is_file()]
                if not paths:raise ValueError('Source local_path must be an existing retrieved/supplied file')
                row['local_path']=paths[0]
        if result.get('artifacts')==[] and isinstance(result.get('summary'),str):
            # Materialize the author's exact summary; never invent an artifact or scientific prose.
            name='_summary_'+hashlib.sha256(result['summary'].encode()).hexdigest()[:12]+'.md'
            result.setdefault('files',{})[name]=result['summary']+'\n'
            result['artifacts']=[name]
            changes.append({'field':'artifacts','rule':'Saved exact author summary as a real file'})
        if changes:result['transport_bindings']=changes
        return result

    def validate(self,result,sid,role,context,inputs):
        errors=[]
        if not isinstance(result.get('summary'),str) or not result['summary'].strip():errors.append('summary must be a nonempty string')
        for field in ['artifacts','evidence','claims','limitations','next_actions']:
            if not isinstance(result.get(field),list):errors.append(field+' must be an array')
        if errors:raise ValueError('; '.join(errors))
        if sid=='08_fresh_continuation':
            memory_inputs=[p for p in inputs if p.name=='fresh_continuation.json']
            if len(memory_inputs)!=1:raise ValueError('Continuation requires its isolated memory packet')
            validate_memory_use(result,read(memory_inputs[0]))
        if role in self.owners:
            validate_notes(result.get('memory_notes',[]),self.memory.index(role)['notes'])
        if role in self.owners and not self.is_memory_probe(sid):
            initial=sid.startswith('02_initial_') and '_learn_' not in sid
            validate_step(result,context['development_cycle'])
            QuestionState(self.run/'question_state',self.owners).validate(sid,role,result,context.get('question_state'),initial)
            HypothesisState(self.run/'hypothesis_state',self.owners).validate(sid,role,result,context['hypothesis_state'])
            service_request(result)
            req=result.get('learning_request',{})
            if sid.startswith('03_exchange_') and not isinstance(req.get('needed'),bool):
                raise ValueError('Exchange learning_request.needed must be a boolean')
            if len(req.get('queries',req.get('search_terms',[])))>2 or len(req.get('urls',[]))>2:
                raise ValueError('Learning request supports at most two queries and two URLs per hop')
            if self.knowledge=='closed' and req.get('needed'):
                raise ValueError('Online search disabled for this explicit closed mode; preserve the gap or use data tools')
            replies=[read(p) for p in inputs if p.parent==self.run/'services/replies']
            expected={s['id'] for r in replies for s in r['sources']}
            if replies:
                rows=result.get('source_use',[])
                if len(rows)!=len(expected) or {r.get('source_id') for r in rows}!=expected:
                    raise ValueError('source_use must match broker reply IDs exactly: '+dumps(sorted(expected)))
                if any(r.get('relation') not in ['direct','method','irrelevant','not_read'] or not r.get('reason') for r in rows):
                    raise ValueError('source_use needs relation direct/method/irrelevant/not_read and a reason')
            if sid in ['05_return_0','05_return_1']:
                validate_uptake(result,read(self.run/'internal_review/report.json'),role,self.run/'internal_review/report.json')
            validate_notes(result.get('memory_notes',[]),self.memory.index(role)['notes'])
        if sid.startswith('01_materials'):
            if not result.get('sources') or not result.get('materials'):raise ValueError('Return nonempty sources and materials')
            missing=[s.get('local_path') for s in result['sources'] if not isinstance(s.get('local_path'),str) or not Path(s['local_path']).is_file()]
            if missing:raise ValueError('Missing source files: '+dumps(missing)+'; use an exact D-document ID returned by search_sources as local_path')
            for row in result['sources']:
                source=read(Path(row['local_path']))
                if Path(row['local_path']).resolve() == (self.run/'allowed/measurements_brief.json').resolve():
                    expected=actor_brief(self.case,read(lab.LAB/'scenarios'/(self.case+'.md')))
                    assert_measurements(self.case,self.root/'cases'/self.case/'measurements.csv')
                    if source != expected:raise ValueError('Registered measurement brief content changed')
                    continue
                reason=self.source_policy.rejection(source)
                if reason:raise ValueError('Material source violates the historical boundary: '+reason)
                KnowledgeBroker.verify_identity(source)
            material_coverage(result)
        if sid=='04_internal_review':
            review=expand_review_packet(read(self.run/'internal_review/inputs.json'));errors=[]
            for f in result.get('findings',[]):
                stage=f.get('source_stage');source=review['sources'].get(stage)
                if source is None:errors.append('Unknown source_stage '+str(stage));continue
                quote=f.get('quote')
                if not isinstance(quote,str) or not quote or not any(quote in p['text'] for p in source['files']):
                    matches=[k for k,v in review['sources'].items() if isinstance(quote,str) and quote and any(quote in p['text'] for p in v['files'])]
                    errors.append('Finding '+str(f.get('id'))+': quote is absent from '+str(stage)+'; exact matching stages: '+dumps(matches))
                keys=[n['key'] for n in source['result'].get('memory_notes',[])]
                if not isinstance(f.get('note_keys'),list) or any(k not in keys for k in f['note_keys']):
                    errors.append('Finding '+str(f.get('id'))+': note_keys refers to actual memory notes, not JSON fields; allowed keys for '+str(stage)+': '+dumps(keys))
            if errors:raise ValueError('; '.join(errors))
            audit_review(result,review)
        if sid=='06_candidates':
            if not isinstance(result.get('ideas'),list):raise ValueError('Return ideas array')
            if result['ideas']:lab.validate_ideas(result)
            refs=[c['ref'] for c in read(self.run/'candidate_history.json')['current_hypotheses']]
            kept=[r.get('ref') for r in result.get('preserved_branches',[])]
            if len(refs)!=len(kept) or any(kept.count(r)!=1 for r in refs):raise ValueError('preserved_branches must account once for every current_hypotheses ref in candidate_history')
        for name,body in result.get('files',{}).items():
            if not isinstance(name,str) or Path(name).is_absolute() or '..' in Path(name).parts or name=='result.json' or not isinstance(body,str):
                raise ValueError('files must use relative artifact names, text bodies, and cannot overwrite result.json')

    @staticmethod
    def validate_artifacts(result,workspace):
        if not result.get('artifacts'):raise ValueError('At least one saved artifact is required')
        for item in result['artifacts']:
            raw=item.get('path') if isinstance(item,dict) else item
            if not isinstance(raw,str) or not raw:raise ValueError('artifact must be a path string or object with path')
            candidate=Path(raw)
            target=(candidate if candidate.is_absolute() else workspace/candidate).resolve()
            if not target.is_relative_to(workspace.resolve()):raise ValueError('Artifact must be inside this stage workspace')
            relative=str(target.relative_to(workspace.resolve()))
            if not target.exists() and relative not in result.get('files',{}):
                raise ValueError('Artifact '+raw+' does not exist; supply its exact text in files')

    def model(self,messages,tools):
        for attempt in range(3):
            try:
                reply=self.api.chat.completions.create(model=self.cfg['model'],messages=messages,tools=tools,
                    parallel_tool_calls=False,max_tokens=12000)
                choice=reply.choices[0]
                if choice.finish_reason=='length':raise ValueError('Model response truncated; no partial result accepted')
                return choice.message.model_dump(exclude_none=True)
            except Exception as exc:
                text=str(exc).lower()
                permanent=any(x in text for x in ['budget_exhausted','insufficient_quota','credit_balance_exhausted','invalid_api_key'])
                transient=any(x in text for x in ['connection error','timed out','concurrency','502','503','504'])
                if permanent or not transient or attempt==2:raise
                time.sleep(2*(attempt+1))

    def __call__(self,run,sid,role,prompt,inputs,model,effort,timeout):
        if sid=='07_check':raise GenerationFrozen()
        workspace=run/'stages'/sid/'api_v2/workspace';workspace.mkdir(parents=True,exist_ok=True)
        result_path=workspace/'result.json'
        sources=[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in inputs]
        fingerprint=hashlib.sha256(dumps({'version':VERSION,'role':role,'prompt':prompt,'sources':sources,'knowledge':self.knowledge,'config':{k:self.cfg.get(k) for k in ['model','api_style','base_url','reasoning_effort','preserve_reasoning_items','continuation_mode']},'transport_code':{name:hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() for name in ['run_ours.py','research_context.py','research_tools.py','submission_repair.py','model_gateway.py','flexible_locator.py']}}).encode()).hexdigest()
        contract=workspace/'TRANSPORT.json'
        if contract.exists() and read(contract)['fingerprint']!=fingerprint:raise ValueError('Stage transport inputs changed; use a new run')
        if result_path.exists():return result_path,read(result_path)
        store=ContextStore(workspace/'documents',admission_guard=self.admit_document,review_indexes=[run/'internal_review/inputs.json']);top=store.prepare(inputs)
        context={}
        for p in inputs:
            if p.parent==run/'researcher_context':context=read(p)
        cycle=context.get('development_cycle',{})
        bindings={'S'+str(i+1):p for i,p in enumerate(cycle.get('sources',{}))}
        expected_sources=sorted({s['id'] for p in inputs if p.parent==run/'services/replies' for s in read(p)['sources']})

        inherited=self.root/'FLEXIBLE_CONTINUATION.json'
        if inherited.exists() and sid in {'01_materials','01_materials_recovery','02_initial_0','02_initial_1'}:
            parent=Path(read(inherited)['parent_run']);prior=parent/'stages'/sid/'api_v2/workspace'
            original=prior/'result.json'
            if not original.exists():
                saved=read(prior/'SESSION.json')['pending_draft']
                original=prior/'drafts'/(saved['sha256']+'.json')
            draft=read(original)
            aliases={str(parent/'allowed/measurements_brief.json'):str(run/'allowed/measurements_brief.json')}
            for name in ['01_materials','01_materials_recovery','02_initial_0']:
                aliases[str(parent/'stages'/name/'api_v2/workspace/result.json')]=str(run/'stages'/name/'api_v2/workspace/result.json')
            def rebind(value):
                if isinstance(value,str):return aliases.get(value,value)
                if isinstance(value,list):return [rebind(v) for v in value]
                if isinstance(value,dict):return {k:rebind(v) for k,v in value.items()}
                return value
            draft=rebind(draft)
            # Retain exact documents previously exposed to this author, including computations.
            manifest=prior/'documents/manifest.json'
            if manifest.exists():
                for ref,row in read(manifest).items():
                    text=(prior/'documents'/(ref+'.txt')).read_text()
                    for path in row['paths']:
                        if path not in aliases:store.add(path,text)
            for item in draft.get('artifacts',[]):
                name=item.get('path') if isinstance(item,dict) else item
                source=prior/name
                if source.is_file():shutil.copy2(source,workspace/name)
            candidate=self.normalize(draft,bindings,store)
            self.validate(candidate,sid,role,context,inputs);self.validate_artifacts(candidate,workspace)
            for filename,body in candidate.pop('files',{}).items():(workspace/filename).write_text(body)
            store.save();write(result_path,candidate)
            write(workspace/'INHERITANCE.json',{'source':str(original),'source_sha256':hashlib.sha256(original.read_bytes()).hexdigest(),'locator_rebindings':aliases,'scientific_content_rewritten':False})
            return result_path,candidate

        memory_probe=self.is_memory_probe(sid)
        tools=ResearchTools(store,workspace,{} if memory_probe else {'measurements':self.root/'cases'/self.case/'measurements.csv'},None if memory_probe else self.broker(workspace),expression,max_calls=64,max_searches=4,source_policy=self.source_policy)
        packet=store.packet(top,max_inline_chars=42000 if sid=='04_internal_review' else 26000)
        packet.update(source_bindings={key:{'path':path,'ref':store.paths[path], 'peer':path in cycle.get('peer_sources',[]),'service':path in cycle.get('required_service_uptake',[])} for key,path in bindings.items()},
                      broker_reply_source_ids=expected_sources,datasets=tools.catalog())
        common=('Use only the tools exposed for this stage. Use read_documents to batch several needed pages in one call, avoiding repeated model round-trips. Use the supplied stage-scoped catalog; do not read arbitrary paths or earlier runs. '
                'The originating study and its explanations are hidden. Retrieval is mechanically restricted to independently dated earlier sources; original-study versions/mirrors and unknown dates are blocked. You may use disciplinary reasoning and clearly labelled conditional hypotheses; lack of an external citation does not prohibit a derivation. '
                'Use search_sources for actual missing public knowledge; returned access depth is explicit, not proof of relevance. analyze_csv reads every selected row, not the 12-row preview. '
                'Submit once using submit_result; if validation fails, the draft is saved locally. Use patch_result with the latest draft_ref and only changed fields; do not regenerate unchanged text. Original submissions remain archived. Every result requires summary (nonempty string) and artifacts, evidence, claims, limitations, next_actions (arrays, empty allowed), plus stage-specific fields. '
                'For development_step focus/uptake source, use a supplied source ID, document ID or unambiguous registered filename. Use a source-field locator instead of copying an exact quote when convenient. '
                'For a JSON source, quote the exact string VALUE, without adding its field name. Alternatively supply quote_pointer (JSON pointer to a string) and omit quote; the exact selected string will be resolved and logged. '
                'For learning_request, context_ref="development_step" may replace duplicate gap/why_now strings; this references your own gap/reason, never changes its content. '
                'For sources[].local_path use the returned D-document ID to avoid copying long paths; it resolves to the exact registered file. '
                'source_use covers exactly broker_reply_source_ids, not the whole source catalog or new searches in this turn. Cite newly read tool sources in evidence/memory_notes with actual paths/URLs. '
                'Keep result text concise; use 0-1 useful memory notes unless multiple are necessary. Preserve branches and open issues. files is an object of relative artifact paths to complete text content; every declared artifact must exist or be provided in files. If artifacts is empty, your exact summary is saved automatically as an artifact; do not repeat the entire JSON as prose. '
                'For review-index-v2, start with the stage directory and read relevant result/before-input sections by document ID. Summaries are incomplete navigation excerpts, not evidence. Start with input_refs and inline bodies, not the entire provenance catalog. When reading a needed document, request the relevant JSON pointer or a useful page (up to 12000 characters); avoid repeated tiny probes. For review, source_stage must match the stage containing the exact quote; note_keys are actual memory_notes keys (often empty), not JSON field names. '
                'If an input body is omitted or represented by $document, read it by ID. No scientific text was summarized; originals and before-inputs remain readable. '\
                +('Online retrieval is enabled.' if self.knowledge=='online' else 'Online retrieval is disabled by explicit --knowledge closed; data/document tools remain available.'))
        if memory_probe:common+=' This is a memory-only continuation: no external search or CSV tool is available.'
        initial=[{'role':'system','content':common+'\n'+prompt},{'role':'user','content':dumps(packet)}]
        initial_path=workspace/'INITIAL_MESSAGES.json'
        if initial_path.exists():
            if read(contract).get('initial_sha256') != hashlib.sha256(initial_path.read_bytes()).hexdigest():
                raise ValueError('Saved initial messages changed')
            initial=read(initial_path)
        else:
            write(initial_path,initial)
        original_chars=sum(len(p.read_text()) for p in inputs)
        write(contract,{'version':VERSION,'fingerprint':fingerprint,'original_input_characters':original_chars,'packed_input_characters':len(dumps(packet)),
                        'documents':len(store.documents),'initial_sha256':hashlib.sha256(initial_path.read_bytes()).hexdigest(),'lossless':True,'knowledge':self.knowledge,'source_bindings':bindings})
        session_path=workspace/'SESSION.json'
        if session_path.exists() and read(session_path)['messages'][:2]!=initial:
            raise ValueError('Historical session inputs changed; use a clean run')
        session=read(session_path) if session_path.exists() else {'messages':json.loads(dumps(initial)),'turns':0,'invalid_submissions':0}
        messages=session['messages']
        # Resume after the last complete tool result; all local tools are content-addressed.
        while session['turns']<72:
            if messages[-1]['role']=='assistant' and messages[-1].get('tool_calls'):
                message=messages[-1]
            else:
                wire_messages = session.get('repair_context', []) + messages[session['repair_start']:] if 'repair_start' in session else messages
                write(workspace/'MODEL_INPUT_LATEST.json', {'messages':wire_messages,'history_messages':len(messages)})
                available = [*tools.definitions, PATCH if session.get('pending_draft') else SUBMIT]
                message=self.model(wire_messages,available)
                # Chat endpoints need standard assistant fields; Responses-only state is kept explicitly.
                message={k:v for k,v in message.items() if k in ['role','content','tool_calls','provider_response_items','reasoning_content']}
                messages.append(message);session['turns']+=1;write(session_path,session)
            calls=message.get('tool_calls') or []
            if not calls:
                messages.append({'role':'user','content':'Use patch_result for the saved draft.' if session.get('pending_draft') else 'Use submit_result to save the stage result.'});write(session_path,session);continue
            for call in calls:
                name=call['function']['name'];call_id=call['id']
                try:
                    args=json.loads(call['function']['arguments'])
                    if name in {'submit_result','patch_result'}:
                        call_hash=hashlib.sha256(dumps({'name':name,'args':args}).encode()).hexdigest()
                        prepared=session.get('prepared_submission',{})
                        if prepared.get('call_id') == call_id:
                            if prepared.get('call_sha256') != call_hash:
                                raise ValueError('Submission call ID reused with different arguments')
                            draft=load_draft(store,session.get('pending_draft'),prepared['draft_ref'])
                        elif name == 'patch_result':
                            draft = load_draft(store, session.get('pending_draft'), args['draft_ref'])
                            draft = apply_edits(draft, args['edits'])
                        else:
                            if session.get('pending_draft'):
                                raise ValueError('A draft is already saved; use patch_result with changed fields only')
                            draft = args['result']
                        session['pending_draft'] = save_draft(workspace, store, draft)
                        session['prepared_submission']={'call_id':call_id,'call_sha256':call_hash,
                                                        'draft_ref':session['pending_draft']['ref']}
                        write(session_path,session)
                        candidate=self.normalize(draft,bindings,store)
                        self.validate(candidate,sid,role,context,inputs)
                        self.validate_artifacts(candidate,workspace)
                        for filename,body in candidate.pop('files',{}).items():
                            target=(workspace/filename).resolve()
                            if not target.is_relative_to(workspace.resolve()):raise ValueError('Artifact escapes workspace')
                            target.parent.mkdir(parents=True,exist_ok=True);target.write_text(body)
                        write(result_path,candidate)
                        write(workspace/'TOOL_EVENTS.json',tools.events)
                        write(workspace/'ACCEPTED.json',{'fingerprint':fingerprint,'role':role,'stage':sid,'validated_before_state_commit':True,'tool_calls':len(list(tools.directory.glob('*.json')))})
                        return result_path,candidate
                    response=tools.call(name,args,call_id)
                except Exception as exc:
                    response={'status':'validation_error' if name in {'submit_result','patch_result'} else 'tool_error','error_type':type(exc).__name__,'message':str(exc)}
                    if name in {'submit_result','patch_result'}:
                        session['invalid_submissions']+=1
                        response.update(allowed_source_keys=list(bindings),broker_reply_source_ids=expected_sources,
                                        draft=session.get('pending_draft'),
                                        advice='Use patch_result with the latest draft ref and only affected fields. Read a draft section if needed. Do not invent evidence or replace unchanged scientific content.')
                messages.append({'role':'tool','tool_call_id':call_id,'content':dumps(response)})
                if name in {'submit_result','patch_result'} and session.get('pending_draft'):
                    # Full original messages are retained; the next model call uses a small repair view.
                    session['repair_start'] = len(messages)
                    session['repair_context'] = repair_context(initial,store,session['pending_draft'],response)
                write(session_path,session)
                if session['invalid_submissions']>=20:raise ValueError('Stage submission recovery limit reached: '+str(response))
        raise ValueError('Stage tool/model turn limit reached without a valid submitted result')

    def generation(self):
        assert_measurements(self.case,self.root/'cases'/self.case/'measurements.csv')
        if not (self.run/'learning_state.json').exists() and any(self.memory.root.rglob('*.json')):
            raise ValueError('Historical comparison requires a fresh researcher store; old knowledge is not imported')
        lab.CASES[self.case]=self.domains
        lab.stage_run=self
        def disabled(url):raise OSError('Explicit closed-corpus mode')
        args=SimpleNamespace(model=self.cfg['model'],effort=self.cfg.get('reasoning_effort','low'),timeout=240,check_timeout=240,
                             executor='api',development_periods=0,continuation_mode=self.cfg.get('continuation_mode','full_context'),knowledge_fetch=self.fetch if self.knowledge=='online' else disabled,knowledge_policy=self.policy)
        try:lab.run_case(self.case,self.run,args,self.memory)
        except GenerationFrozen:pass
        # A frozen generation includes the real internal review and author returns.
        freeze=self.run/'GENERATION_FREEZE.json'
        if not freeze.exists():raise RuntimeError('Generation did not reach its freeze boundary')
        write(self.out/'result.json',{'final':read(self.run/'ideas.json'),'generation_freeze':str(freeze),
                                     'evaluation':'Separate novelty/final evaluation was not run by this interface verification'})

    def correction(self):
        base=[self.root/'cases'/self.case/'dossier.json',self.root/'cases'/self.case/'correction_packet.json']
        history=[]
        for i,instruction in enumerate([
            'Audit every numbered claim against actual data. Use full CSV tools when helpful. Return audit_items with id, correct/incorrect/unsupported verdict, corrected_value and reason. Preserve correct control items.',
            'Inspect the previous audit for specific arithmetic, logical and attribution mistakes. Recompute questionable quantities. Return findings and item-level judgments; do not treat missing proof as refutation of a hypothesis.',
            'Respond to the actual audit review and return final audit_items with id, verdict, corrected_value, reason and implications. Preserve correct controls and unresolved distinctions.'
        ]):
            path,result=self(self.run,'audit_'+str(i),'audit_reviewer' if i==1 else 'audit_author',instruction,
                             [*base,*history],self.cfg['model'],self.cfg.get('reasoning_effort'),240)
            history.append(path)
        write(self.out/'result.json',{'initial':read(history[0]),'review':read(history[1]),'final':read(history[2])})


def main():
    cfg=read(ROOT/'model_config.json')
    p=argparse.ArgumentParser();p.add_argument('--case',choices=['wave','optical'],required=True)
    p.add_argument('--phase',choices=['generation','correction'],default='generation')
    p.add_argument('--knowledge',choices=['online','closed'],default=cfg.get('knowledge','online'));a=p.parse_args()
    adapter=StageAdapter(ROOT,a.case,a.phase,cfg,a.knowledge)
    start=time.monotonic()
    try:
        getattr(adapter,a.phase)();status={'status':'complete'}
    except BaseException as exc:
        status={'status':'budget_exhausted' if 'BUDGET_EXHAUSTED' in str(exc) else 'failed','error':str(exc),'traceback':traceback.format_exc()}
    status.update(seconds=time.monotonic()-start,transport=VERSION,knowledge=a.knowledge,
                  scope='Actual inquiry controller with source/data tools and internal review; terminal novelty evaluation separately reported')
    write(adapter.out/'STATUS.json',status);print(a.case,'ours',status['status'],status.get('error',''),flush=True)
    return 0 if status['status']=='complete' else 1

if __name__=='__main__':raise SystemExit(main())
