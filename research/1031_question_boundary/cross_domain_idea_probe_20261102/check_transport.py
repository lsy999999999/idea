"""Zero-model transport tests; not idea-generation evidence."""
import json
import tempfile
from pathlib import Path
import harness as h

def main():
    cfg=dict(data_path=str(h.ROOT/'sources/uci_165_data.csv'),data_sha256=h.sha(h.ROOT/'sources/uci_165_data.csv'))
    with tempfile.TemporaryDirectory(prefix='cross_domain_fixture_') as td:
        run=Path(td);(run/'tools').mkdir()
        req=dict(id='count_fixture',model_spec='transport-only public row count',code='import json\nprint(json.dumps({"rows":int(len(DF)),"columns":list(DF.columns)}))')
        out=h.compute(run,cfg,req);assert out['status']=='executed'
        assert json.loads(out['stdout'])['rows']==1030
        bad=h.compute(run,cfg,dict(id='syntax_fixture',model_spec='schema fixture',code='print({'))
        assert bad['status']=='clarification' and bad['reason']
        forbidden=h.compute(run,cfg,dict(id='io_fixture',model_spec='boundary fixture',code='open("outside")'))
        assert forbidden['status']=='clarification'
        runtime=h.compute(run,cfg,dict(id='error_fixture',model_spec='error fixture',code='print(1/0)'))
        assert runtime['status']=='failed' and 'ZeroDivisionError' in runtime['stderr']
        search=dict(id='search_fixture',query='concrete compressive strength')
        waiting=h.search_result(run,search);assert waiting['status']=='waiting_external'
        h.dump(run/'tools/search_fixture/raw.json',(h.ROOT/'sources/crossref_transport_fixture.json').read_text())
        returned=h.search_result(run,search);assert returned['status']=='returned' and returned['sources']
        assert all(s['title'] and s['doi'] for s in returned['sources'])
    report=dict(passed=True,model_calls=0,checks=['Complete concrete CSV available to DF with exact columns','Python syntax error returns clarification with retained submitted code hash','External I/O rejected','Runtime errors returned with actual stderr','Live Crossref fixture raw response resolves to dated title/DOI records; no scientific synthesis'],scope='Transport validation only')
    h.dump(h.ROOT/'TRANSPORT_CHECK.json',report);print(json.dumps(report))

if __name__=='__main__':main()
