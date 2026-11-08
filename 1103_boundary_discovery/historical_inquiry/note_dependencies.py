"""Resolve scientific source closures before any persistent note is committed."""
import json
from pathlib import Path

SCHEMA = 'source-closure-v2'


def prepare_dependencies(pilot, result, context):
    broker = pilot.broker
    sources = broker.sources
    by_doi = {source['doi']: source for source in sources.values()}
    data_sources = {'measurements.json', broker.catalog['measurement_context']['data_source']['doi']}
    reports = {record['report_path']: record for record in pilot.evidence.reports()}
    inherited = {}
    for item in context.get('memory', {}).get('retrieved', []):
        if item.get('dependency_schema') != SCHEMA:
            continue
        for citation in item['note']['sources']:
            inherited.setdefault(citation, set()).update(item['source_dependencies'])
    claims = None
    cache = {}

    def atomic(source):
        if source in data_sources:
            return {source}
        record = sources.get(source) or by_doi.get(source)
        if record is None or broker.policy.rejection(record):
            raise ValueError('Unverified or ineligible memory source dependency: ' + str(source))
        return {record['doi']}

    def report_closure(path):
        nonlocal claims
        if path in cache:
            return cache[path]
        record = reports[path]
        if claims is None:
            claims = pilot.evidence.claims()
        # The target's upstream premises are distinct from its affected descendants.
        pending = [finding['claim_ref'] for finding in record['findings']]
        seen, dependencies = set(), set()
        while pending:
            ref = pending.pop()
            if ref in seen:
                continue
            seen.add(ref)
            if ref not in claims:
                raise ValueError('Unknown upstream claim in memory dependency: ' + ref)
            claim = claims[ref]
            for source in claim['basis']['source_ids']:
                dependencies.update(atomic(source))
            if claim['basis'].get('record_ids'):
                broker.check_basis(claim['basis'])
                dependencies.add('measurements.json')
            pending.extend(claim['depends_on'])

        packet_path = pilot.run / 'internal_verification/packets' / (record['boundary'] + '.json')
        catalog = json.loads(packet_path.read_text())['evidence_catalog'] if packet_path.exists() else {}
        for finding in record['findings']:
            for ref in finding['evidence_refs']:
                if ref.startswith('source:'):
                    dependencies.update(atomic(ref[len('source:'):]))
                elif ref.startswith(('motion:', 'window:')):
                    broker.check_basis({'record_ids': [ref.split(':', 1)[1]]})
                    dependencies.add('measurements.json')
                elif ref.startswith('broker:') and ref in catalog:
                    reply = catalog[ref]
                    for source in reply.get('sources', []):
                        dependencies.update(atomic(source['doi']))
                    if reply.get('computed') or reply.get('record_metadata'):
                        dependencies.add('measurements.json')
                else:
                    raise ValueError('Cannot resolve verification evidence dependency: ' + ref)
        cache[path] = dependencies
        return dependencies

    prepared = {}
    for note in result.get('memory_notes', []):
        dependencies = set()
        report_sources = []
        for source in note['sources']:
            if source in data_sources or source in sources or source in by_doi:
                dependencies.update(atomic(source))
            elif source in reports:
                dependencies.update(report_closure(source))
                report_sources.append(source)
            elif source in inherited:
                # NoteGate has verified this exact inherited note and its source result.
                # Recheck every terminal dependency under the current task's date policy.
                for dependency in inherited[source]:
                    dependencies.update(atomic(dependency))
                report_sources.append(source)
            else:
                raise ValueError('Unverified memory dependency: ' + str(source))
        prepared[note['key']] = {
            'dependency_schema': SCHEMA, 'content_screened': True,
            'source_dependencies': sorted(dependencies), 'report_sources': sorted(set(report_sources)),
            'basis': 'Upstream claim closure, cited verifier evidence, and audited inherited note closures.'}
    return prepared
