"""Task-scoped online knowledge retrieval. Raw responses never enter actor context."""
from __future__ import annotations

from datetime import date, datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import re
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from prepare import save


def plain(text):
    return html.unescape(re.sub(r'<[^>]+>', ' ', text or '')).strip()


def doi_key(value):
    return re.sub(r'^(https?://(dx\.)?doi.org/|doi:)', '', str(value).lower()).strip().rstrip('.')


class SourcePolicy:
    def __init__(self, config):
        self.config = config
        self.cutoff = date.fromisoformat(config['knowledge_before_exclusive'])
        self.dois = {doi_key(d) for d in config['excluded_dois']}
        self.titles = [t.casefold() for t in config['excluded_titles']]

    def forbidden(self, value):
        text = json.dumps(value, ensure_ascii=False).casefold()
        return any(d in text for d in self.dois) or any(t in text for t in self.titles)

    def rejection(self, source, *, require_content=True):
        if self.forbidden(source):
            return 'excluded_origin_or_content'
        try:
            d = date.fromisoformat(source['date'])
        except (KeyError, TypeError, ValueError):
            return 'publication_date_unknown'
        if d >= self.cutoff:
            return 'outside_task_date_boundary'
        if require_content and not source.get('text', '').strip():
            return 'no_readable_content'
        return None


class KnowledgeBroker:
    def __init__(self, root, policy, fetch=None):
        self.root, self.policy = Path(root), policy
        self.fetch = fetch or self._fetch
        self.sources = {}
        for p in sorted((self.root / 'accepted').glob('*.json')):
            source = json.loads(p.read_text())
            if self.policy.rejection(source):
                raise ValueError('Cached source no longer satisfies task policy')
            self.verify_identity(source)
            self.sources[source['id']] = source

    @staticmethod
    def verify_identity(source):
        content = {k: v for k, v in source.items() if k not in {'id', 'retrieved_at', 'query'}}
        expected = 'K' + hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()[:16]
        if source['id'] != expected:
            raise ValueError('Accepted source content hash changed')

    @staticmethod
    def _fetch(url):
        req = Request(url, headers={'User-Agent': 'HistoricalInquiry/2.0 (public scientific retrieval)'})
        with urlopen(req, timeout=25) as response:
            data = response.read(4_000_001)
        if len(data) > 4_000_000:
            raise ValueError('Response size exceeded')
        return data.decode('utf-8')

    def _read(self, url, private, label):
        path = private / (label + '.json')
        if path.exists():
            record = json.loads(path.read_text())
            if record['url'] != url:
                raise ValueError('Retrieval cache URL mismatch')
            if 'error' in record:
                raise RuntimeError(record['error'])
            return record['body']
        try:
            body = self.fetch(url)
        except Exception as error:
            save(path, {'url': url, 'retrieved_at': datetime.now(timezone.utc).isoformat(),
                        'error': type(error).__name__ + ': ' + str(error)})
            raise
        save(path, {'url': url, 'retrieved_at': datetime.now(timezone.utc).isoformat(),
                    'body': body, 'sha256': hashlib.sha256(body.encode()).hexdigest()})
        return body

    def search(self, request, request_id):
        """All query topics/types allowed. Unknown dates/content trigger another provider."""
        out = self.root / 'replies' / (request_id + '.json')
        if out.exists():
            result = json.loads(out.read_text())
            if result['request'] != request:
                raise ValueError('Retrieval request changed')
            return result
        queries = request.get('queries', [])
        if not queries and request.get('gap'):
            queries = [request['gap']]
        if isinstance(queries, str):
            queries = [queries]
        if not queries or any(not isinstance(q, str) or not q.strip() for q in queries):
            raise ValueError('Knowledge request needs a query or concrete gap')
        # Identifiers/URLs are search targets, never permission to read unscreened web pages.
        queries = queries + request.get('urls', [])
        accepted, attempts = [], []
        private = self.root / 'controller_only' / request_id
        end = date.fromordinal(self.policy.cutoff.toordinal()-1).isoformat()
        count = self.policy.config.get('retrieval_results_per_query', 5)
        for qi, query in enumerate(queries):
            if self.policy.forbidden(query):
                attempts.append({'query': query, 'status': 'excluded_origin_query'})
                continue
            providers = [
                ('europepmc', 'https://www.ebi.ac.uk/europepmc/webservices/rest/search?' + urlencode({
                    'query': f'({query}) AND FIRST_PDATE:[0001-01-01 TO {end}]',
                    'format': 'json', 'resultType': 'core', 'pageSize': count})),
                ('crossref', 'https://api.crossref.org/works?' + urlencode({
                    'query': query, 'filter': 'until-pub-date:' + end, 'rows': count})),
                ('openalex', 'https://api.openalex.org/works?' + urlencode({
                    'search': query, 'filter': 'to_publication_date:' + end, 'per-page': count})),
            ]
            for provider, url in providers:
                label = f'q{qi}_{provider}'
                try:
                    body = json.loads(self._read(url, private, label))
                    if provider == 'europepmc':
                        rows = body.get('resultList', {}).get('result', [])
                    elif provider == 'crossref':
                        rows = body.get('message', {}).get('items', [])
                    else:
                        rows = body.get('results', [])
                    for ri, row in enumerate(rows):
                        source = self.normalize(provider, row)
                        # Establish identity/date eligibility before trying to acquire text.
                        # Missing index abstracts must not block an available PMC body.
                        reason = self.policy.rejection(source, require_content=False)
                        if reason:
                            # Rejected scientific content is retained only in controller_only.
                            attempts.append({'query': query, 'provider': provider, 'candidate': ri, 'status': reason})
                            continue
                        if provider == 'europepmc' and row.get('pmcid') and self.policy.config.get('read_full_text'):
                            try:
                                pmcid = row['pmcid']
                                if not re.fullmatch(r'PMC\d+', pmcid):
                                    raise ValueError('Invalid PMC identifier')
                                full_url = f'https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML'
                                xml = self._read(full_url, private, label + f'_{ri}_full')
                                full = self.article_text(xml, source)
                                if full:
                                    source.update(text=full, access='article_body_excerpt_up_to_50000_chars', read_url=full_url)
                            except Exception as error:
                                attempts.append({'query': query, 'provider': provider, 'candidate': ri,
                                                 'status': 'full_text_unavailable', 'error_type': type(error).__name__})
                        reason = self.policy.rejection(source)
                        if reason:
                            attempts.append({'query': query, 'provider': provider, 'candidate': ri, 'status': reason})
                            continue
                        source['id'] = 'K' + hashlib.sha256(json.dumps(source, sort_keys=True).encode()).hexdigest()[:16]
                        source['retrieved_at'] = datetime.now(timezone.utc).isoformat()
                        source['query'] = query
                        accepted_path = self.root / 'accepted' / (source['id'] + '.json')
                        if accepted_path.exists():
                            source = json.loads(accepted_path.read_text())
                            self.verify_identity(source)
                        else:
                            save(accepted_path, source)
                        self.sources[source['id']] = source
                        if not any(s['id'] == source['id'] for s in accepted):
                            accepted.append(source)
                    attempts.append({'query': query, 'provider': provider, 'status': 'completed', 'candidates': len(rows)})
                except Exception as error:
                    attempts.append({'query': query, 'provider': provider, 'status': 'retrieval_failed',
                                     'error_type': type(error).__name__})
        result = {'request': request, 'sources': accepted, 'attempts': attempts,
                  'status': 'read_content_returned' if accepted else 'no_eligible_readable_source',
                  'remaining_gap': '' if accepted else 'Continue with a revised query or another source; no knowledge was acquired.',
                  'date_boundary': self.policy.cutoff.isoformat(), 'date_boundary_exclusive': True}
        save(out, result)
        return result

    @staticmethod
    def normalize(provider, row):
        if provider == 'europepmc':
            d, text = row.get('firstPublicationDate'), plain(row.get('abstractText'))
            doi = doi_key(row.get('doi', ''))
            url = 'https://doi.org/' + doi if doi else f'https://europepmc.org/article/{row.get("source")}/{row.get("id")}'
            return {'title': plain(row.get('title')), 'date': d, 'doi': url, 'url': url,
                    'text': text, 'access': 'indexed_abstract_only', 'date_evidence': 'Europe PMC firstPublicationDate'}
        if provider == 'crossref':
            parts = row.get('published', {}).get('date-parts', [[]])[0]
            # Latest possible day for incomplete dates; never guess an early date.
            import calendar
            d = None
            if parts:
                y, m = parts[0], parts[1] if len(parts) > 1 else 12
                day = parts[2] if len(parts) > 2 else calendar.monthrange(y, m)[1]
                d = date(y, m, day).isoformat()
            return {'title': plain(' '.join(row.get('title', []))), 'date': d,
                    'doi': 'https://doi.org/' + doi_key(row.get('DOI', '')), 'url': row.get('URL'),
                    'text': plain(row.get('abstract')), 'access': 'indexed_abstract_only',
                    'date_evidence': 'Crossref published date-parts; incomplete date uses latest possible day'}
        inverted = row.get('abstract_inverted_index') or {}
        words = {pos: word for word, positions in inverted.items() for pos in positions}
        return {'title': row.get('title'), 'date': row.get('publication_date'),
                'doi': row.get('doi') or row.get('id'), 'url': row.get('doi') or row.get('id'),
                'text': ' '.join(words[p] for p in sorted(words)), 'access': 'indexed_abstract_only',
                'date_evidence': 'OpenAlex publication_date'}

    def article_text(self, xml, source):
        root = ET.fromstring(xml)
        ids = [doi_key(e.text) for e in root.findall('.//article-id') if e.get('pub-id-type') == 'doi']
        if doi_key(source['doi']) not in ids or self.policy.forbidden(xml):
            raise ValueError('Full text identity or excluded-content mismatch')
        body = root.find('body')
        if body is None:
            return ''
        # Only article body; omit reference lists, editorial additions and later commentary.
        text = '\n'.join(' '.join(e.itertext()) for e in body.findall('.//p'))
        return text[:50000]  # exact excerpt; explicitly not full paper if truncated
