"""Adversarial historical-access regressions; no network or model calls."""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import quote

import run_ours as runner
from case_access import CASE_RULES, actor_brief, assert_measurements, locked_policy, screen_document
from knowledge_broker import KnowledgeBroker, SourcePolicy
from research_context import ContextStore
from research_tools import ResearchTools

ROOT=Path(__file__).resolve().parents[1]


def source(day='2026-08-11', text='A prior independent relation.'):
    return {'title':'Independent foundation','date':day,'date_evidence':'fixture publication record',
            'doi':'10.1/foundation','url':'https://doi.org/10.1/foundation','text':text,'access':'indexed_abstract_only'}


def xml(day='2026-08-11', extra='', body='Eligible body.'):
    y,m,d=day.split('-')
    return f'<article><front><article-meta><article-id pub-id-type="doi">10.1/foundation</article-id><pub-date><year>{y}</year><month>{m}</month><day>{d}</day></pub-date>{extra}</article-meta></front><body><p>{body}</p></body></article>'


class PolicyTests(unittest.TestCase):
    def test_runtime_configuration_cannot_widen_either_case(self):
        for case, rule in CASE_RULES.items():
            policy=SourcePolicy(locked_policy(case,{'knowledge_before_exclusive':'2099-01-01',
                'excluded_dois':[],'excluded_titles':[],'excluded_identifiers':[],
                'require_date_evidence':False,'require_fulltext_dates':False}))
            self.assertEqual(policy.cutoff.isoformat(),rule['before'])
            self.assertTrue(policy.config['require_date_evidence'])
            self.assertTrue(policy.config['require_fulltext_dates'])
            self.assertTrue(policy.forbidden(rule['dois'][0]))
        with self.assertRaises(KeyError):locked_policy('unregistered_case')

    def test_dates_before_same_day_after_unknown_and_later_version(self):
        p=SourcePolicy(locked_policy('optical'))
        self.assertIsNone(p.rejection(source()))
        for day in ['2026-08-12','2026-08-13',None,'unknown','2026']:
            self.assertIsNotNone(p.rejection(source(day)))
        self.assertEqual(p.rejection({**source(),'publication_dates':['2026-08-13']}),'outside_task_date_boundary')
        self.assertEqual(p.rejection({**source(),'date_evidence':None}),'publication_date_evidence_unknown')

    def test_encoded_doi_title_mirror_and_citation_are_blocked(self):
        p=SourcePolicy(locked_policy('optical'))
        variants=['https://doi.org/'+quote(CASE_RULES['optical']['dois'][0],safe=''),
                  'DEGREE OF POLARIZATION MODULATION FOR HIGH DIMENSIONAL OPTICAL COMPUTING',
                  'Degree-of-<i>polarization</i> modulation for high-dimensional optical computing',
                  'https://example.org/PMC13558076/fulltext',
                  json.dumps({'text':CASE_RULES['optical']['titles'][0]},ensure_ascii=True)]
        for value in variants:
            with self.subTest(value=value):
                self.assertTrue(p.forbidden(value))
                self.assertEqual(p.rejection(source(text=value)),'excluded_origin_or_content')

    def test_conservative_incomplete_and_multiple_publication_dates(self):
        row=KnowledgeBroker.normalize('crossref',{'title':['Prior'], 'abstract':'Known',
            'published':{'date-parts':[[2026]]},'DOI':'10.1/earlier'})
        self.assertEqual(row['date'],'2026-12-31')
        self.assertIsNotNone(SourcePolicy(locked_policy('optical')).rejection(row))
        row=KnowledgeBroker.normalize('crossref',{'title':['Prior'],'abstract':'Known','DOI':'10.1/earlier',
            'published':{'date-parts':[[2026,8,1]]},'published-print':{'date-parts':[[2026,8,15]]}})
        self.assertIsNotNone(SourcePolicy(locked_policy('optical')).rejection(row))

    def test_raw_brief_is_an_explicit_identity_free_measurement_exception(self):
        for case in CASE_RULES:
            original=json.loads((ROOT/'cases'/case/'dossier.json').read_text())
            brief=actor_brief(case,original)
            for before,after in zip(original['preview'],brief['preview']):
                for key,value in before.items():
                    if isinstance(value,float) and not math.isfinite(value):self.assertIsNone(after[key])
                    else:self.assertEqual(after[key],value)
            json.dumps(brief,allow_nan=False)
            self.assertFalse(SourcePolicy(locked_policy(case)).forbidden(brief))
            self.assertNotIn('source',brief)
            assert_measurements(case,ROOT/'cases'/case/'measurements.csv')
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'fake.csv';p.write_text('invented,data\n1,2\n')
            with self.assertRaisesRegex(ValueError,'registered immutable'):assert_measurements('optical',p)


class BrokerTests(unittest.TestCase):
    def test_original_later_unknown_and_related_preprint_never_reach_reply(self):
        calls=[]
        def fetch(url):
            calls.append(url)
            if 'europepmc' not in url:return '{}'
            return json.dumps({'resultList':{'result':[
                {'title':'Independent foundation','doi':'10.1/foundation','firstPublicationDate':'2020-01-01','abstractText':'ELIGIBLE'},
                {'title':'Later','firstPublicationDate':'2026-08-12','abstractText':'LATER_LEAK'},
                {'title':'Undated','abstractText':'UNDATED_LEAK'},
                {'title':CASE_RULES['optical']['titles'][0],'firstPublicationDate':'2020-01-01','abstractText':'ORIGIN_LEAK','pmcid':'PMC13558076'},
                {'title':'Different preprint title','doi':'10.1/preprint','firstPublicationDate':'2020-01-01',
                 'abstractText':'PREPRINT_LEAK','relation':{'is-preprint-of':[{'id':CASE_RULES['optical']['dois'][0]}]}}
            ]}})
        with tempfile.TemporaryDirectory() as td:
            b=KnowledgeBroker(td,SourcePolicy(locked_policy('optical',{'read_full_text':True})),fetch)
            r=b.search({'queries':['independent optics foundation']},'one')
            self.assertEqual([s['text'] for s in r['sources']],['ELIGIBLE'])
            for forbidden in ['LATER_LEAK','UNDATED_LEAK','ORIGIN_LEAK','PREPRINT_LEAK']:
                self.assertNotIn(forbidden,json.dumps(r))
            self.assertEqual(len(calls),3)
            self.assertTrue(any('2026-08-11' in u for u in calls))
            self.assertEqual(r,b.search(r['request'],'one'))

    def test_excluded_origin_query_causes_zero_fetches(self):
        with tempfile.TemporaryDirectory() as td:
            with patch.object(KnowledgeBroker,'_fetch',side_effect=AssertionError('must not fetch')):
                b=KnowledgeBroker(td,SourcePolicy(locked_policy('optical')))
                r=b.search({'queries':[CASE_RULES['optical']['dois'][0]]},'one')
                self.assertEqual(r['sources'],[])
                self.assertEqual(r['attempts'][0]['status'],'excluded_origin_query')

    def test_full_body_requires_own_dates_and_blocks_later_versions(self):
        with tempfile.TemporaryDirectory() as td:
            b=KnowledgeBroker(td,SourcePolicy(locked_policy('optical')))
            self.assertEqual(b.article_text(xml(),source()),'Eligible body.')
            bad=[xml('2026-08-12'),xml(extra='<pub-date><year>2026</year><month>9</month></pub-date>'),
                 xml(extra='<history><date date-type="updated"><year>2026</year><month>9</month></date></history>'),
                 '<article><article-id pub-id-type="doi">10.1/foundation</article-id><body><p>Undated body</p></body></article>']
            for text in bad:
                with self.assertRaises(ValueError):b.article_text(text,source())

    def test_old_index_does_not_authorize_reading_later_body(self):
        def fetch(url):
            if 'fullTextXML' in url:return xml('2026-09-01',body='LATER_BODY_LEAK')
            if 'europepmc' in url:return json.dumps({'resultList':{'result':[{
                'title':'Foundation','doi':'10.1/foundation','firstPublicationDate':'2020-01-01',
                'abstractText':'EARLIER_ABSTRACT','pmcid':'PMC123'}]}})
            return '{}'
        with tempfile.TemporaryDirectory() as td:
            r=KnowledgeBroker(td,SourcePolicy(locked_policy('optical',{'read_full_text':True})),fetch).search({'queries':['foundation']},'one')
            self.assertEqual(r['sources'][0]['text'],'EARLIER_ABSTRACT')
            self.assertNotIn('LATER_BODY_LEAK',json.dumps(r))

    def test_reply_cache_cannot_escape_changed_cutoff(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'replies/one.json';path.parent.mkdir()
            path.write_text(json.dumps({'request':{'queries':['foundation']},'sources':[],
                'policy_fingerprint':'old-unrestricted-policy'}))
            b=KnowledgeBroker(td,SourcePolicy(locked_policy('optical')),lambda _: (_ for _ in ()).throw(AssertionError('no fetch')))
            with self.assertRaisesRegex(ValueError,'policy changed'):b.search({'queries':['foundation']},'one')


class InputAndCacheTests(unittest.TestCase):
    def test_nested_sources_are_gated_before_inline_or_page_delivery(self):
        p=SourcePolicy(locked_policy('optical'))
        guard=lambda path,text:screen_document(p,text)
        with tempfile.TemporaryDirectory() as td:
            store=ContextStore(td,admission_guard=guard)
            for value in [source('2026-08-13'),{'before_inputs':[{'text':json.dumps(source(None))}]}]:
                with self.assertRaises(ValueError):store.add('/source',json.dumps(value))
            ref=store.add('/earlier',json.dumps(source()))
            store.prepare([])
            self.assertIn('prior independent',store.read(ref,raw=True)['text'])
            # Workflow timestamps are not scientific publication dates.
            screen_document(p,json.dumps({'created_at':'2026-11-09','summary':'An inference formed now.'}))

    def test_existing_document_manifest_is_rechecked(self):
        with tempfile.TemporaryDirectory() as td:
            old=ContextStore(td);old.add('/old',json.dumps(source('2026-09-01')));old.save()
            with self.assertRaises(ValueError):ContextStore(td,admission_guard=lambda path,text:screen_document(SourcePolicy(locked_policy('optical')),text))

    def test_tool_cache_is_bound_to_the_effective_policy(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);store=ContextStore(root/'docs');ref=store.add('/generated','Some generated reasoning.')
            loose=SourcePolicy(locked_policy('optical'));tight=SourcePolicy(locked_policy('optical',{'knowledge_before_exclusive':'2025-01-01'}))
            args={'ref':ref,'pointer':'','offset':0,'limit':100,'raw':True}
            ResearchTools(store,root,{},source_policy=loose).call('read_document',args,'first')
            with self.assertRaisesRegex(ValueError,'policy changed'):
                ResearchTools(store,root,{},source_policy=tight).call('read_document',args,'second')

    def test_final_gateway_rejects_before_model_client_or_cache(self):
        spec=importlib.util.spec_from_file_location('guarded_gateway',Path(runner.__file__).with_name('model_gateway.py'))
        g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
        for group,body in [('optical/ours/generation',json.dumps(source('2026-09-01'))),
                           ('optical/ours/generation',CASE_RULES['optical']['titles'][0]),
                           ('optical/evoscientist/generation','Anything')]:
            with patch.object(g,'client',side_effect=AssertionError('must not contact model')):
                with self.assertRaises(ValueError):g.invoke(group,{'messages':[{'role':'user','content':body}]})


if __name__=='__main__':unittest.main()
