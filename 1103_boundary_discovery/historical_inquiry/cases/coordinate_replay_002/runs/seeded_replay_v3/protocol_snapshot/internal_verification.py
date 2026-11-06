"""Bounded internal evidence checks. No novelty judgment or authority over ideas."""
from __future__ import annotations

import copy
from pathlib import Path

from prepare import save
from question_state import read, file_hash, object_hash


PROTOCOL = """
INTERNAL EVIDENCE PROTOCOL v1:
You may raise a concrete doubt while discussing; you are not required to criticize.
Return evidence_claims: [] or objects {id: local short ID, text: exact factual assertion or
hypothesis, kind: observation/inference/hypothesis, use: exploratory/research_decision,
consequence: what decision rests on it (empty for exploratory),
basis: {source_ids: [F1/F2/F3/F4 or data.csv], spectrum_ids: []}, depends_on: [exact earlier claim refs]}.
A claim ref is stage_id:local_id. Use supplied earlier claims to record actual reliance.
claims is the generic runtime array; put the structured entries in evidence_claims.
Include factual premises used to abandon a line or change a question, even if peers agree.
Return doubts: [] or {claim_ref: exact earlier ref or this stage's local ID,
type: evidence_discrepancy/unproved_hypothesis, reason: concrete mismatch,
consequence: why resolving it matters}. Missing proof for a conjecture is NOT an error;
unproved_hypothesis is deferred without a verifier call. No mandatory objection each turn.
Verification is limited and advisory. A correction may withdraw a motivation while leaving
the question alive. Never infer that a coherent tentative idea must be discarded.
"""

VERIFY_TASK = """You are an on-demand internal evidence verifier, separate from the final
idea evaluator. Verify ONLY the supplied target claims against the original approved material
and reproducible controller arithmetic. The arithmetic is sampled-peak processing, not a fit
or scientific conclusion. Check comparison coordinates, conditions, units and reasoning.
Return findings: [{claim_ref, status: supported/needs_correction/undetermined,
reason: concrete reproducible reasoning, evidence_refs: exact keys from evidence_catalog,
corrected_claim: a scoped replacement string for needs_correction, otherwise null}].
Include exactly one finding per target. No novelty or idea-acceptance judgment. Missing proof,
data, implementation or experimental validation of a tentative hypothesis is not an error.
Insufficient material means undetermined. Do not claim general collapse from two spectra.
You may be wrong: show enough reasoning for peers to disagree with your finding.
"""

UPTAKE_TASK = """A focused evidence report is returned to the COMMON DISCUSSION, not to an
owner of the overall question. Read every finding and earlier peer replies. Return
verification_responses: [{claim_ref, stance: accept/rebut/unresolved, reason: evidence-based,
changed_understanding: scoped change or reason for no change,
question_effect: retain/revise/unresolved}]. Respond to every finding; no forced agreement.
stance refers to the verifier's finding: accept means accepting that finding, NOT accepting
the original mistaken claim. You may also respond to other supplied claim refs, clearly
explain their separate scope; these are discussion responses, not extra verifier findings.
Separate an incorrect supporting argument from a still coherent question or hypothesis.
Update memory_notes for EVERY supplied affected note using its SAME key and revision_reason,
kind correction, citing the supplied verification_report_path plus approved raw sources.
Preserve the note's usable content and conditions. If you rebut or cannot decide, record the
dispute explicitly; do not present either version as settled. You may add new notes too.
Even if affected_notes is empty, save at least one sourced correction/dispute note about
your actual response to this report, with kind correction and verification_report_path.
Do not claim your peer agreed unless they actually did. Continue discussing or revising your
explanation; ordinary question updates do not automatically change a peer's question.
"""


class EvidenceLedger:
    def __init__(self, root, max_checks=2, batch_size=2):
        self.root = Path(root)
        self.max_checks = max_checks  # batches per run, not one critic call per turn
        self.batch_size = batch_size

    def events(self):
        events = sorted((self.root / 'events').glob('*.json'))
        values = [read(p) for p in events]
        values.sort(key=lambda e: e['sequence'])
        for i, value in enumerate(values, 1):
            if value['sequence'] != i or file_hash(value['source_result']) != value['source_sha256']:
                raise ValueError('Evidence ledger provenance changed')
        return values

    def claims(self):
        return {c['ref']: c for e in self.events() for c in e['claims']}

    def validate(self, stage, researcher, result):
        previous = next((e for e in self.events() if e['stage'] == stage), None)
        if previous:
            if previous['researcher'] != researcher or previous['result_hash'] != object_hash(result):
                raise ValueError('Recorded evidence result changed')
            return
        claims, doubts = result.get('evidence_claims', []), result.get('doubts', [])
        if not isinstance(claims, list) or not isinstance(doubts, list):
            raise ValueError('Evidence claims/doubts must be arrays')
        known = self.claims()
        local = set()
        for c in claims:
            cid = c.get('id')
            if not isinstance(cid, str) or not cid.replace('_', '').isalnum() or cid in local:
                raise ValueError('Invalid/duplicate local evidence ID')
            local.add(cid)
            if not isinstance(c.get('text'), str) or not c['text'].strip():
                raise ValueError('Missing evidence claim text')
            if c.get('kind') not in {'observation', 'inference', 'hypothesis'} or c.get('use') not in {'exploratory', 'research_decision'}:
                raise ValueError('Invalid evidence claim type/use')
            if c['use'] == 'research_decision' and not c.get('consequence'):
                raise ValueError('Consequential claim needs a decision reason')
            deps = c.get('depends_on')
            if not isinstance(deps, list) or any(d not in known for d in deps):
                raise ValueError('Evidence dependency must cite an earlier exact claim ref')
            basis = c.get('basis', {})
            if not isinstance(basis, dict) or any(not isinstance(basis.get(k), list) for k in ('source_ids', 'spectrum_ids')):
                raise ValueError('Evidence basis needs source_ids and spectrum_ids arrays')
            # Backward references within this response are allowed; future/cyclic refs are not.
            known[stage + ':' + cid] = c
        for d in doubts:
            if d.get('claim_ref') not in known and d.get('claim_ref') not in local:
                raise ValueError('Doubt must identify an exact claim')
            if d.get('type') not in {'evidence_discrepancy', 'unproved_hypothesis'} or not d.get('reason') or not d.get('consequence'):
                raise ValueError('Doubt needs type, reason and consequence')

    def observe(self, stage, researcher, result, path):
        self.validate(stage, researcher, result)
        target = self.root / 'events' / (stage + '.json')
        if target.exists():
            return
        claims = [{**c, 'ref': stage + ':' + c['id'], 'stage': stage, 'author': researcher}
                  for c in result.get('evidence_claims', [])]
        doubts = [{**d, 'claim_ref': (stage + ':' + d['claim_ref'] if ':' not in d['claim_ref'] else d['claim_ref']),
                   'raised_by': researcher, 'stage': stage} for d in result.get('doubts', [])]
        save(target, {'sequence': len(self.events()) + 1, 'stage': stage, 'researcher': researcher,
                      'source_result': str(Path(path).resolve()), 'source_sha256': file_hash(path),
                      'result_hash': object_hash(result), 'claims': claims, 'doubts': doubts})

    def history_packet(self, stage, independent=False):
        path = self.root / 'inputs' / (stage + '.json')
        if not path.exists():
            save(path, {'claims': [] if independent else list(self.claims().values()),
                        'checks': [] if independent else self.reports()})
        return read(path)

    def reports(self):
        values = [read(p) for p in sorted((self.root / 'reports').glob('*.json'))]
        for r in values:
            if file_hash(r['report_path']) != r['report_sha256']:
                raise ValueError('Internal verification report changed')
        return values

    def select(self, boundary):
        path = self.root / 'batches' / (boundary + '.json')
        if path.exists():
            return read(path)
        claims = self.claims()
        checked = {f['claim_ref'] for r in self.reports() for f in r['findings']}
        pending = {}
        deferred = []
        for e in self.events():
            for d in e['doubts']:
                if d['type'] == 'unproved_hypothesis':
                    deferred.append({**d, 'disposition': 'not_an_error_or_gate'})
                elif d['claim_ref'] not in checked:
                    pending.setdefault(d['claim_ref'], []).append(d)
        # Consensus is not evidence: check important factual premises even without objections.
        for ref, c in claims.items():
            if c['kind'] != 'hypothesis' and c['use'] == 'research_decision' and ref not in checked:
                pending.setdefault(ref, []).append({'type': 'consequential_premise', 'reason': c['consequence']})
        limit = self.batch_size if len(self.reports()) < self.max_checks else 0
        selected = list(pending)[:limit]
        value = {'boundary': boundary, 'targets': [claims[r] for r in selected],
                 'triggers': {r: pending[r] for r in selected},
                 'pending_refs': list(pending)[len(selected):], 'deferred': deferred,
                 'budget_exhausted': bool(pending and not limit)}
        save(path, value)
        return value

    def relevant(self, refs):
        """Transitive declared dependencies. Mark for reconsideration, never auto-refute."""
        claims = self.claims()
        affected = set(refs)
        while True:
            more = {r for r, c in claims.items() if set(c['depends_on']) & affected}
            if more <= affected:
                return [copy.deepcopy(c) for r, c in claims.items() if r in affected]
            affected |= more

    def validate_findings(self, result, targets, catalog):
        findings = result.get('findings')
        if not isinstance(findings, list) or len(findings) != len(targets) or {f.get('claim_ref') for f in findings} != {t['ref'] for t in targets}:
            raise ValueError('Internal finding coverage mismatch')
        for f in findings:
            if f.get('status') not in {'supported', 'needs_correction', 'undetermined'} or not f.get('reason'):
                raise ValueError('Invalid internal finding')
            refs = f.get('evidence_refs')
            if not isinstance(refs, list) or any(r not in catalog for r in refs):
                raise ValueError('Finding cites evidence outside supplied packet')
            if f['status'] != 'undetermined' and not refs:
                raise ValueError('A definite finding requires supplied evidence')
            if f['status'] == 'needs_correction' and not f.get('corrected_claim'):
                raise ValueError('A correction needs a scoped replacement')

    def record_report(self, boundary, result, path):
        record = {'boundary': boundary, 'report_path': str(Path(path).resolve()),
                  'report_sha256': file_hash(path), 'findings': result['findings']}
        target = self.root / 'reports' / (boundary + '.json')
        if target.exists() and read(target) != record:
            raise ValueError('Internal report changed')
        save(target, record)
        return record


def evidence_packet(case, targets, claims, broker):
    """Reproduce simple quantities from immutable data; never execute agent-authored code."""
    needed = {c['ref']: c for c in targets}
    pending = list(needed.values())
    while pending:
        for dep in pending.pop()['depends_on']:
            if dep not in needed:
                needed[dep] = claims[dep]
                pending.append(claims[dep])
    sources = sorted({s for c in needed.values() for s in c['basis']['source_ids']})
    ids = sorted({i for c in needed.values() for i in c['basis']['spectrum_ids']})
    materials = broker(case, {'source_ids': [s for s in sources if s != 'data.csv'],
                              'spectrum_ids': ids, 'all_rows': 'data.csv' in sources and not ids})
    catalog = {f'source:{s["id"]}': s for s in materials['sources']}
    if 'data.csv' in sources:
        catalog['data.csv'] = {'sha256': file_hash(case / 'allowed/data.csv'),
                               'scope': 'Full CSV' if not ids else 'Requested spectra reproduced below',
                               'csv': materials['all_rows_csv']}
    for s in materials['spectra']:
        c = s['conditions']
        peak_level = max(level for _, level in s['frequency_and_level'])
        peaks = [f for f, level in s['frequency_and_level'] if level == peak_level]
        catalog[f'spectrum:{s["id"]}'] = s
        catalog[f'arithmetic:{s["id"]}'] = {
            'method': 'all sampled argmax(level); x_chord = f * chord / velocity; x_thickness = f * thickness / velocity',
            'units': 'frequency Hz; chord/thickness m; velocity m/s; transformed x dimensionless',
            'sampled_peak_hz': peaks, 'sampled_peak_level': peak_level,
            'peak_f_chord_over_U': [f*c['chord-length']/c['free-stream-velocity'] for f in peaks],
            'peak_f_thickness_over_U': [f*c['suction-side-displacement-thickness']/c['free-stream-velocity'] for f in peaks],
            'limits': 'sampled maximum only, not a continuous peak estimate; full spectral collapse is not established'}
    return {'targets': targets, 'dependency_claims': list(needed.values()),
            'evidence_catalog': catalog,
            'data_sha256': file_hash(case / 'allowed/data.csv'),
            'spectra_sha256': file_hash(case / 'allowed/spectra.json'),
            'sources_sha256': file_hash(case / 'allowed/sources.json')}
