"""Offline controller/transport regressions; no claims about scientific performance."""
import copy
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import run_ours as runner
from research_context import ContextStore, dumps
from submission_repair import apply_edits, save_draft, load_draft, repair_context
from learning_support import review_packet, expand_review_packet, audit_review


class PatchTests(unittest.TestCase):
    def test_only_selected_fields_change_and_invalid_edit_is_atomic(self):
        original = {'summary': [], 'hypotheses': [{'claim': 'A causes B under C.'}], 'a/b': {'~key': 1}}
        updated = apply_edits(original, [{'op': 'set', 'path': '/summary', 'value': 'Brief'},
                                         {'op': 'set', 'path': '/a~1b/~0key', 'value': 2}])
        self.assertEqual(updated['hypotheses'], original['hypotheses'])
        self.assertEqual(original['summary'], [])
        self.assertEqual(updated['a/b']['~key'], 2)
        with self.assertRaises((ValueError, KeyError)):
            apply_edits(original, [{'op': 'set', 'path': '/summary', 'value': 'Brief'},
                                   {'op': 'remove', 'path': '/absent'}])
        self.assertEqual(original['summary'], [])
        for path in ['', '/hypotheses/-1', '/hypotheses/01', '/a~9b']:
            with self.assertRaises(ValueError):
                apply_edits(original, [{'op': 'set', 'path': path, 'value': 'x'}])

    def test_draft_versions_and_targeted_read_survive_restart(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); store = ContextStore(root/'documents')
            draft = {'hypotheses': [{'claim': 'An unchanged scientific hypothesis.'}], 'summary': []}
            first = save_draft(root, store, draft)
            amended = apply_edits(draft, [{'op': 'set', 'path': '/summary', 'value': 'Brief'}])
            second = save_draft(root, store, amended)
            restored = ContextStore(root/'documents'); restored.prepare([])
            with self.assertRaisesRegex(ValueError, 'Stale'):
                load_draft(restored, second, first['ref'])
            self.assertEqual(load_draft(restored, second, second['ref']), amended)
            self.assertEqual(json.loads(restored.read(first['ref'], pointer='/hypotheses/0/claim')['text']),
                             'An unchanged scientific hypothesis.')

    def test_repair_view_omits_full_draft_but_retains_readable_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); store = ContextStore(root/'documents')
            ref = store.add(str(root/'evidence.txt'), 'Contradicting source with a qualification.')
            draft = {'summary': [], 'claim': 'A large unchanged hypothesis. '*5000}
            pending = save_draft(root, store, draft)
            messages = repair_context([{'role': 'system', 'content': 'Research task'}], store, pending,
                                      {'message': 'summary must be a nonempty string'})
            self.assertNotIn(draft['claim'], dumps(messages))
            self.assertLess(len(dumps(messages)), len(dumps(draft))//10)
            self.assertIn(ref, dumps(messages))
            self.assertIn('qualification', store.read(ref)['text'])


class ReviewIndexTests(unittest.TestCase):
    def build(self, root, count=12):
        material = root/'source.json'
        material.write_text(json.dumps({'theory': 'Original relation and limitations. '*4000}))
        stages = {}; inputs = {}
        for i in range(count):
            result = root/f'stage_{i}'/'result.json'; result.parent.mkdir()
            result.write_text(json.dumps({'summary': f'Stage {i} hypothesis', 'memory_notes': [],
                                         'claims': ['If A, then B. Tail qualification preserved.']}))
            stages[f's{i}'] = ('author', result); inputs[f's{i}'] = [material]
        return review_packet(stages, inputs), material

    def test_shared_sources_indexed_once_and_originals_on_demand(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); packet, material = self.build(root)
            self.assertEqual(len(packet['documents']), 13)
            before=[s['before_inputs'][0]['$document'] for s in packet['sources'].values()]
            self.assertEqual(len(set(before)), 1)
            self.assertNotIn('Original relation', dumps(packet))
            path=root/'review.json'; path.write_text(dumps(packet))
            store=ContextStore(root/'documents',review_indexes=[path]); top=store.prepare([path]); view=store.packet(top)
            self.assertNotIn('Original relation', dumps(view))
            material_ref=store.paths[str(material.resolve())]
            self.assertIn('Original relation', store.read(material_ref,pointer='/theory',limit=100)['text'])
            # The default view does not implicitly re-inline all result bodies.
            self.assertNotIn('Tail qualification preserved.',dumps(view))
            section=json.loads(store.read(top[0],pointer='/sources/s0/result')['text'])
            self.assertIn('Tail qualification',store.read(section['$document'],pointer='/claims')['text'])
            with self.assertRaisesRegex(ValueError,'controller-designated'):
                ContextStore(root/'untrusted').prepare([path])
            finding={'id':'f','source_stage':'s0','quote':'If A, then B.', 'kind':'logic',
                     'status':'undetermined','reason':'Check condition','note_keys':[]}
            self.assertEqual(audit_review({'findings':[finding]},packet)['findings'][0]['status'],'undetermined')
            material.write_text('{}')
            with self.assertRaisesRegex(ValueError,'source changed'):expand_review_packet(packet)
            with self.assertRaisesRegex(ValueError,'source changed'):
                ContextStore(root/'new_documents',review_indexes=[path]).prepare([path])


class RepairResumeTests(unittest.TestCase):
    def test_restart_between_saving_draft_and_validation_does_not_resubmit(self):
        class Interrupted(BaseException): pass
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); case=root/'cases/optical'; case.mkdir(parents=True)
            shutil.copy2(runner.ROOT/'cases/optical/measurements.csv',case/'measurements.csv')
            source=root/'input.json'; source.write_text('{"task":"Fixture"}')
            value={'summary':'Author content',**{k:[] for k in ['artifacts','claims','evidence','limitations','next_actions']}}
            message={'role':'assistant','tool_calls':[{'id':'same_call','type':'function','function':{
                     'name':'submit_result','arguments':json.dumps({'result':value})}}]}
            calls=[]
            def create(**kw):
                calls.append(kw)
                return SimpleNamespace(choices=[SimpleNamespace(finish_reason='tool_calls',
                    message=SimpleNamespace(model_dump=lambda **kw:message))])
            api=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
            with patch.object(runner,'PROJECT',root/'project'):
                adapter=runner.StageAdapter(root,'optical','generation',{'model':'fake'},'closed',api)
                args=(adapter.run,'test','auditor','Research',[source],'fake','low',20)
                with patch.object(adapter,'validate',side_effect=Interrupted):
                    with self.assertRaises(Interrupted):adapter(*args)
                restored=runner.StageAdapter(root,'optical','generation',{'model':'fake'},'closed',api)
                _,result=restored(*args)
                self.assertEqual(result['summary'],value['summary'])
                self.assertEqual(len(calls),1)

    def test_interrupt_after_rejection_then_patch_preserves_hypothesis(self):
        class Interrupted(BaseException): pass
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); case=root/'cases/optical'; case.mkdir(parents=True)
            shutil.copy2(runner.ROOT/'cases/optical/measurements.csv',case/'measurements.csv')
            source=root/'input.json'; source.write_text('{"task":"A fixture task"}')
            scientific='An author hypothesis that must remain exactly unchanged. '*300
            draft={'summary':[], 'claims':[scientific], 'evidence':[], 'limitations':[], 'next_actions':[], 'artifacts':[]}
            attempts=[]
            def create(**kw):
                attempts.append(copy.deepcopy(kw))
                if len(attempts)==1:
                    name,args='submit_result',{'result':draft}
                elif len(attempts)==2:
                    self.assertNotIn(scientific,dumps(kw['messages']))
                    raise Interrupted()
                else:
                    info=json.loads(kw['messages'][-1]['content'])
                    name,args='patch_result',{'draft_ref':info['draft']['ref'],
                                            'edits':[{'op':'set','path':'/summary','value':'A concise summary'}]}
                message={'role':'assistant','tool_calls':[{'id':'c'+str(len(attempts)),'type':'function',
                         'function':{'name':name,'arguments':json.dumps(args)}}]}
                # Include a provider reasoning item to catch replaying the large failed response by another channel.
                message['provider_response_items']=[{'type':'function_call','call_id':message['tool_calls'][0]['id'],
                    'name':name,'arguments':json.dumps(args)}]
                return SimpleNamespace(choices=[SimpleNamespace(finish_reason='tool_calls',
                    message=SimpleNamespace(model_dump=lambda **kw:message))])
            api=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
            with patch.object(runner,'PROJECT',root/'project'):
                adapter=runner.StageAdapter(root,'optical','generation',{'model':'fake'},'closed',api)
                args=(adapter.run,'test','auditor','Research',[source],'fake','low',20)
                with self.assertRaises(Interrupted): adapter(*args)
                stage=adapter.run/'stages/test/api_v2/workspace'
                self.assertFalse((stage/'result.json').exists())
                adapter=runner.StageAdapter(root,'optical','generation',{'model':'fake'},'closed',api)
                path,result=adapter(*args)
                self.assertEqual(result['claims'],draft['claims'])
                self.assertIn(scientific,(stage/'SESSION.json').read_text())
                self.assertNotIn(scientific,dumps(attempts[-1]['messages']))
                self.assertEqual(result['summary'],'A concise summary')


if __name__=='__main__':unittest.main()
