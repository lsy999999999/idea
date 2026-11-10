"""Controller-owned historical boundaries. Research/model configuration cannot widen them."""
from copy import deepcopy
from datetime import date
import hashlib
import json
import math
from types import MappingProxyType

CASE_RULES = MappingProxyType({
    'optical': MappingProxyType({
        'before': '2026-08-12',
        'dois': ('10.1038/s41586-026-10891-z',),
        'titles': ('Degree-of-polarization modulation for high-dimensional optical computing',),
        'aliases': ('PMC13558076', 'zenodo.org/records/20775840', '10.5281/zenodo.20775840'),
        'csv_sha256': 'a5a301fc89d6a71010b845198aed9711bf9c8aebe0dbb6c8021dc32f7fb437c0',
    }),
    'wave': MappingProxyType({
        'before': '2026-10-14',
        'dois': ('10.1038/s41586-026-11163-6', '10.5281/zenodo.17398589'),
        'titles': ('Wave coarsening drives time crystallization in mechatronic metamaterials',),
        'aliases': ('zenodo.org/records/22541069', '10.5281/zenodo.22541069'),
        'csv_sha256': '3cebf6a1fdce58f279f217542d47b76f1f0f763fe3c023865d9b02150fd1a9ab',
    }),
})


def locked_policy(case, requested=None):
    rule = CASE_RULES[case]  # New cases must first register a controller-owned boundary.
    cfg = deepcopy(requested or {})
    requested_date = date.fromisoformat(cfg.get('knowledge_before_exclusive', rule['before']))
    cfg.update(historical_case=case,
               knowledge_before_exclusive=min(requested_date, date.fromisoformat(rule['before'])).isoformat(),
               require_date_evidence=True, require_fulltext_dates=True)
    for key, required in [('excluded_dois', rule['dois']), ('excluded_titles', rule['titles']),
                          ('excluded_identifiers', rule['aliases'])]:
        cfg[key] = sorted(set(cfg.get(key, [])) | set(required))
    return cfg


def actor_brief(case, dossier):
    """Explicit raw-measurement exception; no source identity, explanation or conclusions."""
    fields = ('data_dictionary', 'rows', 'statistics', 'preview', 'data_file')
    brief = {key: deepcopy(dossier[key]) for key in fields if key in dossier}
    brief.update(case=case, knowledge_before_exclusive=CASE_RULES[case]['before'],
                 task='Develop explanatory hypotheses, conditional consequences and questions from these measurements. Re-deriving an existing result can be a valid outcome; assess prior-work overlap only after generation.',
                 measurement_scope='Separate source scans are measurements, not independent repeated preparations. Supplied raw measurements are the only exception to the historical publication boundary.',
                 retrieval_policy='Only independently dated sources strictly before the historical boundary are readable. The hidden originating study, its versions, mirrors and identifying references are blocked. Unknown dates are blocked. Use the screened tools only.')
    def finite_json(value):
        if isinstance(value,dict):return {k:finite_json(v) for k,v in value.items()}
        if isinstance(value,list):return [finite_json(v) for v in value]
        if isinstance(value,float) and not math.isfinite(value):return None
        return value
    return finite_json(brief)


def assert_measurements(case, path):
    if hashlib.sha256(path.read_bytes()).hexdigest() != CASE_RULES[case]['csv_sha256']:
        raise ValueError('Historical raw-measurement exception requires the registered immutable CSV')


def screen_document(policy, text):
    """Gate originals before projection, model input, paging, and cache restoration."""
    if policy.forbidden(text):
        raise ValueError('Historical input contains excluded origin identifiers/content; start a clean run')
    try:
        value = json.loads(text)
    except (ValueError, TypeError):
        return
    def visit(item):
        if isinstance(item, list):
            for child in item:
                visit(child)
        elif isinstance(item, dict):
            # Public records have a text body and source metadata. Internal tool pages
            # have ref/offset/text, not publication metadata.
            if 'text' in item and any(key in item for key in ('doi', 'url', 'access')):
                reason = policy.rejection(item)
                if reason:
                    raise ValueError('Historical source input rejected: ' + reason)
            for child in item.values():
                visit(child)
        elif isinstance(item, str) and item.lstrip().startswith(('{', '[')):
            try:
                nested = json.loads(item)
            except ValueError:
                return
            if not isinstance(nested, str):
                visit(nested)
    visit(value)
