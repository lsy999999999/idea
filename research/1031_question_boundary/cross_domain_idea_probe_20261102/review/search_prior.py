"""Separately labeled post-run literature triage, outside the 36-role experiment."""
import concurrent.futures
import json
from pathlib import Path
import subprocess
import urllib.parse

ROOT = Path(__file__).resolve().parent
QUERIES = {
 'materials': 'early age strength supplementary cementitious materials seven 28 days strength development qualification',
 'health_replicate': 'Parkinson voice telemonitoring repeated recordings test retest reliability within subject',
 'health_trigger': 'Parkinson personalized voice monitoring change detection clinical assessment alerts',
 'education': 'school tutoring chronic absenteeism attendance intervention randomized trial academic outcomes',
 'energy_thermal': 'household appliance heat indoor temperature lag event detection energy monitoring',
 'energy_submeter': 'event based sampling smart meter appliance monitoring adaptive sampling submetering',
 'environment': 'Beijing pollution episode termination wind direction shift clearance PM2.5',
}


def fetch(item):
    key, query = item
    params = dict({'query.bibliographic': query, 'rows': 5,
                   'select': 'DOI,title,published,abstract,type',
                   'filter': 'until-pub-date:2026-11-02'})
    url = 'https://api.crossref.org/works?' + urllib.parse.urlencode(params)
    path = ROOT / ('postrun_prior_' + key + '.json')
    if path.exists():
        raise RuntimeError('Refusing to replace '+str(path))
    p = subprocess.run(['curl', '--fail', '--location', '--silent', '--show-error',
                        '--max-time', '30', url, '--output', str(path)],
                       capture_output=True, text=True)
    row = dict(key=key, query=query, url=url, returncode=p.returncode,
               stderr=p.stderr, output_file=str(path))
    print(key, p.returncode, flush=True)
    return row


def main():
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        records = list(pool.map(fetch, QUERIES.items()))
    primary = ROOT / 'transport_prior_primary.json'
    p = subprocess.run(['curl', '--fail', '--location', '--silent', '--show-error',
                        '--max-time', '30',
                        'https://api.crossref.org/works/10.1016%2Fj.jtrangeo.2020.102854',
                        '--output', str(primary)], capture_output=True, text=True)
    records.append(dict(key='transport_primary', returncode=p.returncode,
                        stderr=p.stderr, output_file=str(primary)))
    with (ROOT/'POSTRUN_SEARCH_LOG.json').open('x') as f:
        json.dump(dict(scope='Post-run organizer triage; never fed back to frozen roles; original tool counts unchanged.',
                       records=records), f, ensure_ascii=False, indent=2)


if __name__=='__main__':main()
