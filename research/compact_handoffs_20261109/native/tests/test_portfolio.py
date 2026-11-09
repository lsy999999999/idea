"""Queue/barrier, provenance and budget regressions; scientific actors here are fixtures."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from discover import read,write
from learning_memory import Memory,digest
from learning_support import review_packet
from portfolio_contracts import validate_progress,validate_ranker
from portfolio_runtime import BatchRuntime,PendingRoles,immutable
from research_portfolio import Portfolio,schedule,feedback_from_rankers


def base():
    return {'summary':'Fixture output','artifacts':['NOTE.md'],'evidence':[], 'claims':[],
            'limitations':[],'next_actions':[]}


def ranking(packet):
    ids=[d['id'] for d in packet['directions']]
    anchors={d['id']:d['seed']['assumption'] for d in packet['directions']}
    return {**base(),'assessments':[{'direction_id':i,
        **{k:{'status':'unclear','quotes':[],'reason':'Early unresolved direction'} for k in
           ('problem','conceptual_move','development_space')},'uncertainty':'Unknown potential',
        'future_possibilities':[]} for i in ids],
        'comparisons':[{'a':a,'b':b,'preference':'prefer_a','reason':'Specific conditional relation',
            'counterargument':'Less explicit alternative may develop differently',
            'anchors':[{'direction_id':i,'quote':anchors[i]} for i in (a,b)]}
             for j,a in enumerate(ids) for b in ids[j+1:]],
        'suggestions':[{'id':'s1','direction_id':ids[0],'origin':'ranker_conjecture',
            'text':'Consider a different relation','basis_quotes':[anchors[ids[0]]]}]}


def fixture(req):
    packet=read(req['input']); kind=req['kind']; result=base()
    if kind=='ranker':
        result=ranking(packet)
    elif kind=='developer':
        key=packet['direction']['id']+'__h'
        old=next((c for c in packet['hypothesis_state']['self'] if c['ref']['key']==key),None)
        result.update(hypothesis_updates=[{'key':key,'base_version':old['ref']['version'] if old else 0,
            'assumption':'A conditional relation '+req['stage'],'motivation':'Distinct outcome',
            'conceptual_move':None,'implications':[],'open_questions':[],
            'status':'parked' if packet['direction']['id']=='D002' else 'developing',
            'reason':'Keep uncertainty','influenced_by':[]}],
            memory_notes=[{'key':'shared_concept','title':'Shared concept','kind':'hypothesis','mastery':'explained',
                'understanding':'Tentative '+req['stage'],'conditions':'Unresolved','example':'Thought example',
                'open_questions':'Consequences?','tags':[],'sources':[],'revision_reason':'Develop'}],
            feedback_responses=[{'ref':s['ref'],'stance':'decline','reason':'Alternative interpretation'}
                                for s in packet['feedback']['suggestions']],source_use=[])
        from cycle_fixture import development_step
        result['development_step'] = development_step(packet['development_cycle'])
        if packet['phase']=='draft':
            result['analysis_plan']={'kind':'calculation','question':'Example','bindings':{'x':[1,2]},
                                     'expression':'sum(x)','expected':3}
    elif kind=='progress':
        result.update(findings=[], reviewed_stages=list(packet['sources']),changes=[
            {'stage':s,'classification':'unclear','after_quote':'Fixture output',
             'reason':'Fixture has no scientific content','before_evidence':[]} for s in packet['sources']])
    elif kind=='uptake':
        result.update(memory_notes=[],verification_responses=[])
    elif kind=='recorder':
        result.update(ideas=[],preserved_directions=[d['id'] for d in packet['directions']],
            preserved_branches=[{'ref':c['ref'],'reason':'Retained'} for c in packet['current_hypotheses']])
    return result


class PortfolioTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)

    def emit(self,runtime,request,result=None):
        req=read(request); ws=Path(req['workspace']);(ws/'NOTE.md').write_text('Fixture artifact')
        write(ws/'result.json', result or fixture(req));runtime.deliver(req['stage'],'fixture')

    def test_json_roundtrip_keeps_tuple_configuration_resumable(self):
        p=self.root/"config.json"
        immutable(p,{"researchers":[("A","chemistry")]})
        immutable(p,{"researchers":[("A","chemistry")]})
        with self.assertRaises(ValueError):immutable(p,{"researchers":[("A","physics")]})

    def test_role_preflight_is_read_only_and_available_before_delivery(self):
        rt=BatchRuntime(self.root)
        request=rt.prepare('test','generic','A','test',{})
        req=read(request);ws=Path(req['workspace']);(ws/'NOTE.md').write_text('artifact')
        write(ws/'result.json',base())
        before={str(p):digest(p) for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(rt.preflight('test')['status'],'valid')
        self.assertEqual(before,{str(p):digest(p) for p in self.root.rglob('*') if p.is_file()})
        self.assertIn('--validate-only',req['validation_command'])
        write(ws/'result.json',{**base(),'summary':{}})
        with self.assertRaises(ValueError):rt.preflight('test')
        self.assertFalse((request.parent/'DELIVERY.json').exists())
        self.assertFalse((request.parent/'rejected').exists())

    def test_barrier_invalid_delivery_and_changed_inputs(self):
        rt=BatchRuntime(self.root)
        jobs=[dict(stage=i,kind='generic',owner=i,prompt='test',packet={'same':'snapshot'}) for i in ('a','b')]
        with self.assertRaises(PendingRoles):rt.batch('batch',jobs)
        requests=[Path(p) for p in read(self.root/'PENDING_ROLES.json')['requests']]
        self.emit(rt,requests[0],base())
        with self.assertRaises(PendingRoles):rt.batch('batch',jobs)
        req=read(requests[1]);ws=Path(req['workspace']);(ws/'NOTE.md').write_text('note')
        write(ws/'result.json',{**base(),'summary':{}})
        with self.assertRaises(ValueError):rt.deliver('b','fixture')
        self.assertFalse((requests[1].parent/'DELIVERY.json').exists())
        self.assertEqual(len(list((requests[1].parent/'rejected').glob('*.json'))),1)
        self.emit(rt,requests[1],base())
        self.assertEqual(set(rt.batch('batch',jobs)),{'a','b'})
        Path(req['input']).write_text('{}')
        with self.assertRaisesRegex(ValueError,'inputs changed'):rt.batch('batch',jobs)

    def test_before_memory_blocks_false_new_relation(self):
        before=self.root/'before.json';write(before,{'memory':'Absolute agreement differs from rank consistency.'})
        after=self.root/'result.json';write(after,{**base(),'learning_change':'Absolute agreement differs from rank consistency.'})
        packet=review_packet({'learn':('researcher',after)},{'learn':[before]})
        result={'findings':[],'reviewed_stages':['learn'],'changes':[{'stage':'learn','classification':'new_relation',
            'after_quote':'Absolute agreement differs from rank consistency.','reason':'Claimed new',
            'before_evidence':[{'path':str(before),'quote':'Absolute agreement differs from rank consistency.'}]}]}
        with self.assertRaisesRegex(ValueError,'already-supplied'):validate_progress(result,packet)
        result['changes'][0]['classification']='restatement';validate_progress(result,packet)
        result['changes'][0]['before_evidence'][0]['quote']='Not supplied'
        with self.assertRaisesRegex(ValueError,'Before quote'):validate_progress(result,packet)

    def test_ranking_requires_both_anchors_and_retains_unclear(self):
        packet={'directions':[{'id':i,'seed':{'assumption':i+' concept'}} for i in ('D001','D002')]}
        result=ranking(packet);validate_ranker(result,packet)
        result['comparisons'][0]['anchors'].pop()
        with self.assertRaisesRegex(ValueError,'BOTH'):validate_ranker(result,packet)

    def test_ranker_future_possibilities_return_even_without_suggestions(self):
        possibility = {'origin':'ranker_conjecture','text':'A possible new relation', 'basis_quotes':['seed']}
        result = {'suggestions':[], 'assessments':[{'direction_id':'D001','future_possibilities':[possibility]}]}
        feedback=feedback_from_rankers({'rank0':(None,result)},['D001'])['D001']
        self.assertEqual(feedback[0]['text'],possibility['text'])
        self.assertEqual(feedback[0]['ref'],{'stage':'rank0','id':'future:D001:0'})
        self.assertEqual(feedback[0]['origin'],'ranker_conjecture')
        self.assertNotIn('preference',feedback[0])

    def test_known_common_sources_do_not_break_service_classification(self):
        from portfolio_contracts import validate_developer
        packet={'direction':{'id':'D001'},'hypothesis_state':{'self':[],'peer_branches':[]},
            'feedback':{'suggestions':[]},'common':[{'id':'common'}],
            'service_replies':[{'sources':[{'id':'service'}]}], 'memory':{'available_index':{}}}
        result={'hypothesis_updates':[],'feedback_responses':[],
            'source_use':[{'source_id':i,'relation':'method','reason':'Read'} for i in ('service','common')]}
        validate_developer(result,packet)
        result['source_use'][1]['source_id']='invented'
        with self.assertRaises(ValueError):validate_developer(result,packet)
        result['source_use']=[]
        with self.assertRaises(ValueError):validate_developer(result,packet)

    def test_rotation_revives_low_rank_and_disagreement_not_fake_score(self):
        ds=[{'id':f'D{i:03d}','seed':{'assumption':'a'}} for i in range(1,6)]
        rank=ranking({'directions':ds}); counts={}
        allocations=[]
        for period in range(4):
            selected=schedule(ds,[rank,rank],counts,2,period)['selected']
            allocations.extend(x['direction_id'] for x in selected)
            for x in selected:counts[x['direction_id']]=counts.get(x['direction_id'],0)+1
        self.assertEqual(set(allocations),{d['id'] for d in ds})
        reverse=copy.deepcopy(rank)
        for c in reverse['comparisons']:c['preference']='prefer_b'
        self.assertTrue(all(v==0 for v in schedule(ds,[rank,reverse],{},4,0)['unanimous_pair_wins'].values()))

    def run_fixture(self,periods,budget):
        memory=Memory(self.root/'memory');researchers=[['A','chemistry'],['B','measurement']]
        seeds=[{'id':i,'seed':{'assumption':i+' conditional relation'}} for i in ('D001','D002','D003')]
        cfg={'periods':periods,'rounds':2,'slots':2,'call_budget':budget,'model':'fixture','effort':'low',
             'timeout':1,'knowledge_policy':{'knowledge_before_exclusive':'2026-11-07',
             'excluded_dois':[],'excluded_titles':[],'retrieval_results_per_query':1,'read_full_text':False}}
        for _ in range(60):
            engine=Portfolio(self.root/'development',memory,researchers,seeds,[],cfg,
                             fetch=lambda u:self.fail('No retrieval intended'))
            try:
                output=engine.run();return engine,output
            except PendingRoles:
                requests=[Path(p) for p in read(engine.root/'PENDING_ROLES.json')['requests']]
                # No hypotheses from partial batch are admitted even after one delivery.
                before=engine.hypotheses.current()
                for req in requests:self.emit(engine.runtime,req)
                self.assertEqual(before,engine.hypotheses.current())
        self.fail('Did not finish')

    def test_two_period_resume_parallel_memory_conflict_feedback_and_budget(self):
        engine,out=self.run_fixture(2,44)
        self.assertEqual(read(engine.root/'STOP.json')['logical_calls_before_recording'],42)
        self.assertEqual(len(list((engine.root/'roles').glob('*/DELIVERY.json'))),43)
        self.assertIn('D003',read(engine.root/'STOP.json')['opportunities'])
        self.assertTrue(any(c['status']=='parked' for c in engine.hypotheses.current()))
        rows=[r for p in (engine.root/'admissions').glob('*.json') for r in read(p)['rows']]
        self.assertTrue(all(r['deferred_notes'] for r in rows))
        self.assertFalse(engine.memory.index('A')['notes'])
        packets=[read(p) for p in (engine.root/'roles').glob('p00_r0_draft_*/input.json')]
        self.assertTrue(all(not p['hypothesis_state']['self'] for p in packets))
        self.assertTrue(all(p['peer_drafts']==[] for p in packets))
        exchanges=[read(p) for p in (engine.root/'roles').glob('p00_r0_exchange_*/input.json')]
        self.assertTrue(all(len(p['peer_drafts'])==2 for p in exchanges))
        self.assertTrue(all(p['service_replies'][0]['computed'][0]['result']['actual']==3 for p in exchanges))
        for packet in exchanges:
            cycle = packet['development_cycle']
            self.assertEqual(len(cycle['previous_steps']), 1)
            self.assertTrue(cycle['required_service_uptake'])
            self.assertTrue(cycle['peer_sources'])
            self.assertEqual(packet['service_replies'][0]['development_context']['gap'],
                             cycle['previous_steps'][0]['step']['gap'])
        later = read(engine.root/'roles/p00_r1_draft_D001_0/input.json')['development_cycle']
        self.assertTrue(later['repeated_no_change'])
        self.assertEqual(len(later['previous_steps']), 2)
        rank_packet=read(engine.root/'roles/p01_rank_0/input.json')
        self.assertNotIn('comparisons',json.dumps(rank_packet))
        before={str(p):digest(p) for p in (engine.root/'hypotheses').rglob('*.json')}
        engine.run()
        self.assertEqual(before,{str(p):digest(p) for p in (engine.root/'hypotheses').rglob('*.json')})

    def test_parked_direction_keeps_unconsumed_learning_reply(self):
        from unittest.mock import patch
        original = fixture
        def with_tail(req):
            value = original(req)
            if req['kind'] == 'developer' and read(req['input'])['phase'] == 'exchange':
                value['analysis_plan'] = {'kind': 'calculation', 'question': 'Unfinished example',
                                         'bindings': {'x': [2, 3]}, 'expression': 'sum(x)'}
            return value
        with patch(__name__+'.fixture', side_effect=with_tail):
            engine, _ = self.run_fixture(2, 44)
        pending = read(engine.root/'STOP.json')['unconsumed_service_replies']
        self.assertIn('D002', pending)
        self.assertEqual(len(pending['D002']), 2)
        self.assertTrue(all(r['development_context']['gap'] for r in pending['D002']))

    def test_no_partial_period_when_budget_insufficient(self):
        engine,out=self.run_fixture(1,22)
        self.assertEqual(len(list((engine.root/'roles').glob('*/DELIVERY.json'))),1)
        self.assertEqual(read(engine.root/'STOP.json')['opportunities'],{})
        self.assertEqual(len(out[1]['preserved_directions']),3)


if __name__=='__main__':unittest.main()
