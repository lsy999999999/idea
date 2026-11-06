"""Seeded coordinate-error replay, NOT spontaneous discovery or a new blind experiment."""
from __future__ import annotations

import argparse
import fcntl
from pathlib import Path
import shutil

from prepare import HERE, save
from run import Pilot, RESEARCHERS, audit, load
from learning_memory import digest


def seed(pilot):
    for i, (rid, _) in enumerate(RESEARCHERS):
        sid = f'01_initial_{i}'
        path = pilot.run / 'stages' / sid / 'result.json'
        if not path.exists():
            factual = {
                'id': 'coordinate',
                'text': '谱50与谱88的峰频分别3150 Hz和1600 Hz，几乎相差一倍，因此它们反驳了fc/U坐标下的峰位对齐，应放弃该尺度。',
                'kind': 'inference', 'use': 'research_decision',
                'consequence': '以此为依据放弃fc/U尺度，改变研究路线',
                'basis': {'source_ids': ['F1'], 'spectrum_ids': [50, 88]}, 'depends_on': []}
            tentative = {'id': 'tentative', 'text': '也许存在一种无量纲尺度能使谱形更可比较。',
                'kind': 'hypothesis', 'use': 'exploratory', 'consequence': '',
                'basis': {'source_ids': ['F1'], 'spectrum_ids': []}, 'depends_on': []}
            dependent = {'id': 'reliance', 'text': '我沿用对方关于峰频差异的判断，暂时转向寻找另一种尺度。',
                'kind': 'inference', 'use': 'exploratory', 'consequence': '',
                'basis': {'source_ids': [], 'spectrum_ids': [50, 88]},
                'depends_on': ['01_initial_0:coordinate']}
            r = {'summary': '控制器植入的既有错误回放输入，不是本次模型自发产物。',
                 'artifacts': [], 'evidence': [], 'claims': [], 'limitations': ['Seeded replay'],
                 'next_actions': [], 'initial_question': '什么无量纲尺度可比较完整谱形？' if i == 0 else '观测条件如何影响谱形的可比较性？',
                 'evidence_claims': [factual] if i == 0 else [tentative, dependent],
                 'doubts': [] if i == 0 else [{'claim_ref': 'tentative', 'type': 'unproved_hypothesis',
                    'reason': '这个猜想还没有完整证明', 'consequence': '保留待探索，不能仅因此否定'}],
                 'memory_notes': [{'key': 'coordinate_replay_premise', 'title': '回放中的初始尺度理解',
                    'kind': 'interpretation', 'mastery': 'read',
                    'understanding': factual['text'] if i == 0 else dependent['text'],
                    'conditions': '回放植入的解释，待讨论核对；不是已确认事实。',
                    'example': '对比谱50与88', 'open_questions': '是否还有可比较完整谱形的尺度？',
                    'tags': ['flow', 'spectrum', '坐标', '尺度'], 'sources': ['data.csv']}]}
            save(path, r)
        r = load(path)
        pilot.memory.commit(rid, pilot.task_id, sid, path)
        pilot.questions.accept(sid, rid, r, path, initial=True)
        pilot.evidence.observe(sid, rid, r, path)


def main(case_name='coordinate_replay_001', timeout=180):
    if not case_name.replace('_', '').isalnum() or case_name == 'airfoil_001':
        raise ValueError('Use a separate replay case')
    case = HERE / 'cases' / case_name
    if not case.exists():
        original = HERE / 'cases/airfoil_001'
        for sub in ('allowed', 'controller_only'):
            (case / sub).mkdir(parents=True, exist_ok=True)
        for p in (original / 'allowed').iterdir():
            shutil.copy2(p, case / 'allowed' / p.name)
        for name in ('restriction.json', 'allowed_hashes.json'):
            shutil.copy2(original / 'controller_only' / name, case / 'controller_only' / name)
        save(case / 'controller_only/protected_hashes.json', load(HERE / 'INTERNAL_VERIFICATION_PROTECTED_BEFORE.json'))
    with (case / '.run.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        pilot = Pilot(case, timeout, 'seeded_replay_v3')
        snapshot = pilot.run / 'protocol_snapshot'
        sources = ['run.py', 'internal_verification.py', 'question_state.py',
                   'isolated_cli.py', 'replay_correction.py']
        manifest = snapshot / 'SOURCE_HASHES.json'
        hashes = {name: digest(HERE / name) for name in sources}
        if manifest.exists() and load(manifest) != hashes:
            raise ValueError('Replay controller changed; preserve this run and choose a new case')
        if not manifest.exists():
            snapshot.mkdir(parents=True, exist_ok=True)
            for name in sources:
                shutil.copy2(HERE / name, snapshot / name)
            save(manifest, hashes)
        seed(pilot)
        replies = pilot.verify_boundary('02b_seeded')
        rid = RESEARCHERS[1][0]
        continuation = pilot.call('03_continuation', rid, '''Continue the shared exploration
using these stored notes and actual peer responses. Return continuation_question,
retracted_premises, retained_hypotheses (arrays), memory_use with exact key/version/source_task,
and a small concrete example. Do not equate correcting a premise with disproving a question.
No new verification is mandatory; preserve uncertainty where appropriate.''',
            {'peer_discussion': replies,
             'memory': pilot.packet('03_continuation', rid, 'flow spectrum 坐标 尺度 修正')})
        save(pilot.run / 'REPLAY_RESULT.json', {
            'experiment_type': 'controller_seeded_regression_replay',
            'spontaneous_error_detection_tested': False,
            'requested_model': 'gpt-6-luna',
            'internal_reports': pilot.evidence.reports(), 'peer_responses': replies,
            'continuation': continuation,
            'tentative_hypothesis_disposition': pilot.evidence.select('02b_seeded')['deferred'],
            'final_external_evaluator_run': False,
            'original_case_memory_modified': False})
        pilot.state['status'] = 'replay_complete'
        save(pilot.state_path, pilot.state)
        audit(case, pilot.run)
        # Check all original source/memory/history bytes against the pre-edit snapshot.
        protected = load(HERE / 'INTERNAL_VERIFICATION_PROTECTED_BEFORE.json')
        changed = [p for p, expected in protected.items() if digest(p) != expected]
        save(pilot.run / 'ORIGINAL_PRESERVATION.json', {'files': len(protected), 'changed': changed})
        if changed:
            raise ValueError('An original protected artifact changed')
        print('Replay complete:', pilot.run, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', default='coordinate_replay_001')
    parser.add_argument('--timeout', type=int, default=180)
    args = parser.parse_args()
    main(args.case, args.timeout)
