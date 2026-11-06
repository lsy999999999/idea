"""Run-local, owner-specific hypothesis branches beside existing questions and memory."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import re

from question_state import file_hash, object_hash, read


PROTOCOL = """
HYPOTHESIS DEVELOPMENT v1:
Use your disciplinary understanding and screened long-term memory to develop assumptions.
Start from a specific phenomenon, tension, difficulty or missing relation. When you have a
possible explanation or organizing principle, state what you suppose; merely changing a
'whether' question into an affirmative sentence adds no insight. An assumption can be an
explanation, conjectured relation, representation, distinction or method/construction principle.
Explore what conceptual move it makes and, CONDITIONALLY on the assumption, what changes in
our understanding or possible actions. Develop concrete consequences, not promises of impact.
Use these as thinking moves, not a checklist that every early idea must already satisfy.

In peer discussion, engage a specific assumption: elaborate a consequence, expose a hidden
premise, connect a disciplinary concept, propose a distinct explanation, or revise a relation.
Explain the reasoning. You may retain, revise, branch, or park your own line. No forced consensus,
disagreement, novelty claim, completed hypothesis or compulsory new branch each turn.
Evidence strength, proof, available data/tools, implementation and experimental feasibility
are NOT requirements for proposing, retaining or prioritizing a hypothesis. Do not turn
discussion into a feasibility review. Research/analysis requests remain optional resources
for thinking. Correct concrete errors in premises while keeping conditional hypotheses distinct
from established observations; lack of evidence alone is not a refutation.

hypothesis_state.self contains your saved branches; peer_branches belong to their named owners.
Return hypothesis_updates: [] when nothing changed, otherwise full cards:
{key: stable local identifier [A-Za-z0-9_]+, base_version: 0 for new or supplied own version,
assumption: nonempty provisional claim, motivation: specific phenomenon/difficulty/relation,
conceptual_move: string or null if still unclear,
implications: [specific conditional consequences, may be empty],
open_questions: [unresolved conceptual questions, may be empty],
status: developing/parked, reason: why propose/change/park/resume,
influenced_by: [exact ref objects from supplied hypothesis_state]}.
Omitting a branch retains it. To keep an alternative, use a new key and cite the parent ref;
never overwrite a peer's branch. Missing conceptual_move or implications is allowed for an
early assumption. Keep hypothetical consequences explicitly hypothetical, including examples.
Reusable conceptual learning can also be saved through existing memory_notes, kind:hypothesis,
with actual source provenance and same-key revisions. Run-local branches do not replace your
long-term disciplinary memory or its source screening. Do not invent empirical support.
"""

CONTENT = ('assumption', 'motivation', 'conceptual_move', 'implications', 'open_questions', 'status')


class HypothesisState:
    def __init__(self, root, researchers):
        self.root = Path(root)
        self.researchers = list(researchers)

    @staticmethod
    def _safe(value):
        if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_]+', value):
            raise ValueError('Unsafe hypothesis stage/key')

    @staticmethod
    def _write(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('x') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)

    def events(self):
        events = sorted((read(p) for p in (self.root/'events').glob('*.json')),
                        key=lambda e: e['sequence'])
        for i, event in enumerate(events, 1):
            if event['sequence'] != i or file_hash(event['source_result']) != event['source_sha256']:
                raise ValueError('Hypothesis history or source result changed')
        return events

    def current(self):
        state = {}
        for event in self.events():
            for card in event['updates']:
                state[(card['ref']['owner'], card['ref']['key'])] = card
        return list(state.values())

    def packet(self, stage, researcher, independent=False):
        self._safe(stage)
        if researcher not in self.researchers:
            raise ValueError('Unknown hypothesis owner')
        path = self.root/'inputs'/(stage+'.json')
        if path.exists():
            packet = read(path)
            if packet['researcher'] != researcher or packet['independent'] != independent:
                raise ValueError('Hypothesis packet owner/visibility changed')
            return packet
        cards = self.current()
        packet = {'researcher': researcher, 'independent': independent,
                  'self': [c for c in cards if c['ref']['owner'] == researcher],
                  'peer_branches': [] if independent else
                  [c for c in cards if c['ref']['owner'] != researcher]}
        self._write(path, packet)
        return packet

    def history_packet(self, stage):
        self._safe(stage)
        path = self.root/'inputs'/(stage+'_history.json')
        if not path.exists():
            self._write(path, {'hypothesis_history': self.events(),
                               'current_hypotheses': self.current()})
        return read(path)

    def validate(self, stage, researcher, result, packet):
        self._safe(stage)
        if researcher not in self.researchers:
            raise ValueError('Unknown hypothesis owner')
        previous = next((e for e in self.events() if e['stage'] == stage), None)
        if previous:
            if previous['researcher'] != researcher or previous['result_object_sha256'] != object_hash(result):
                raise ValueError('Already recorded hypothesis result changed')
            return
        if not packet or packet['researcher'] != researcher:
            raise ValueError('Missing owner-specific hypothesis state')
        updates = result.get('hypothesis_updates', [])
        if not isinstance(updates, list):
            raise ValueError('hypothesis_updates must be an array')
        supplied = {c['ref']['key']: c for c in packet['self']}
        current = {c['ref']['key']: c for c in self.current() if c['ref']['owner'] == researcher}
        known = [c['ref'] for c in packet['self'] + packet['peer_branches']]
        keys = set()
        for card in updates:
            if not isinstance(card, dict):
                raise ValueError('Hypothesis card must be an object')
            self._safe(card.get('key'))
            key = card['key']
            if key in keys:
                raise ValueError('Duplicate hypothesis key in stage')
            keys.add(key)
            if 'owner' in card or 'ref' in card:
                raise ValueError('Hypothesis ownership is controller assigned')
            base = supplied[key]['ref']['version'] if key in supplied else 0
            actual = current[key]['ref']['version'] if key in current else 0
            if type(card.get('base_version')) is not int or card['base_version'] != base or actual != base:
                raise ValueError('Wrong or stale hypothesis base version')
            for name in ('assumption', 'motivation', 'reason'):
                if not isinstance(card.get(name), str) or not card[name].strip():
                    raise ValueError('Hypothesis needs ' + name)
            if card.get('conceptual_move') is not None and not isinstance(card['conceptual_move'], str):
                raise ValueError('conceptual_move must be text or null')
            for name in ('implications', 'open_questions'):
                if not isinstance(card.get(name), list) or any(not isinstance(v, str) or not v.strip() for v in card[name]):
                    raise ValueError('Hypothesis needs text array ' + name)
            if card.get('status') not in {'developing', 'parked'}:
                raise ValueError('Invalid hypothesis status')
            if not isinstance(card.get('influenced_by'), list) or any(r not in known for r in card['influenced_by']):
                raise ValueError('Hypothesis influence must cite supplied refs')

    def accept(self, stage, researcher, result, result_path, packet):
        self.validate(stage, researcher, result, packet)
        path = self.root/'events'/(stage+'.json')
        if path.exists():
            return read(path)
        current = {c['ref']['key']: c for c in self.current() if c['ref']['owner'] == researcher}
        updates = []
        for card in result.get('hypothesis_updates', []):
            content = {k: copy.deepcopy(card.get(k)) for k in CONTENT}
            old = current.get(card['key'])
            # Rewording only the update reason or citations is not conceptual progress.
            if old and all(content[k] == old[k] for k in CONTENT):
                continue
            updates.append({**content, 'ref': {'owner': researcher, 'key': card['key'],
                            'version': card['base_version'] + 1},
                            'reason': card['reason'], 'influenced_by': copy.deepcopy(card['influenced_by']),
                            'source_stage': stage, 'source_result': str(Path(result_path).resolve())})
        event = {'stage': stage, 'researcher': researcher, 'sequence': len(self.events()) + 1,
                 'source_result': str(Path(result_path).resolve()), 'source_sha256': file_hash(result_path),
                 'result_object_sha256': object_hash(result), 'before': copy.deepcopy(packet),
                 'decisions': copy.deepcopy(result.get('hypothesis_updates', [])), 'updates': updates}
        self._write(path, event)
        return event
