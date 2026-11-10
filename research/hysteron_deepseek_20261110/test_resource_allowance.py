import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parent/'runtime'))
import run_with_resource_allowance as resource
from research_context import ContextStore


class Response:
    status_code = 200
    def __enter__(self):return self
    def __exit__(self,*args):return None
    def raise_for_status(self):return None
    def iter_content(self,size):yield b'{"message":"ok"}'


class ResourceAllowanceTests(unittest.TestCase):
    def setUp(self):
        self.fetcher = resource.inquiry.PublicFetcher
        self.tools = resource.inquiry.ResearchTools
        resource.install_resource_allowance()

    def tearDown(self):
        resource.inquiry.PublicFetcher = self.fetcher
        resource.inquiry.ResearchTools = self.tools

    def test_fetch_241_preserves_history_and_host_restriction(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'fetches.json'
            old=[{'url':'historical-record','status':'read'} for _ in range(240)]
            path.write_text(json.dumps(old))
            fetch=resource.inquiry.PublicFetcher(path)
            with patch.object(resource.inquiry.requests,'get',return_value=Response()):
                self.assertIn('ok',fetch('https://api.crossref.org/works'))
            rows=json.loads(path.read_text())
            self.assertEqual(rows[:240],old)
            self.assertEqual(len(rows),241)
            with self.assertRaises(ValueError):fetch('https://unregistered.example/works')

    def test_resource_failed_search_gets_separate_retry_and_old_cache_survives(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            tools=resource.inquiry.ResearchTools(ContextStore(root/'documents'),root,{},None)
            args={'queries':['hysteron coupling']}
            key=hashlib.sha256(json.dumps({'name':'search_sources','args':args},sort_keys=True).encode()).hexdigest()
            old=tools.directory/(key+'.json');old.write_text('{"retained":"old failed tool record"}')
            original=old.read_bytes()
            audit=root/'knowledge/controller_only'/('tool_'+key[:16]);audit.mkdir(parents=True)
            (audit/'q0_crossref.json').write_text(json.dumps({'error':'ValueError: Run retrieval request budget exhausted'}))
            calls=[]
            def search(request,request_id):
                calls.append(request_id)
                return {'sources':[],'attempts':[],'status':'no_eligible_readable_source','remaining_gap':'No matching source'}
            tools.broker=SimpleNamespace(root=root/'knowledge',search=search)
            result=tools.call('search_sources',args,'new-call')
            self.assertEqual(result['status'],'no_eligible_readable_source')
            tools.call('search_sources',args,'replayed-call')
            self.assertEqual(len(calls),1)
            self.assertEqual(old.read_bytes(),original)
            self.assertTrue((tools.directory/'resource_allowance_retry'/(key+'.json')).exists())


if __name__=='__main__':unittest.main()
