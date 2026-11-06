"""Replay frozen plans through dispatch without resuming historical researchers."""
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
from fish_inquiry import InquiryPilot, load
from fish_materials import CASE, digest
from inquiry_services import InquiryBroker
from prepare import save


def main():
    config = load(ROOT.parent/'configs/fish_v2.json')
    pilot = InquiryPilot.__new__(InquiryPilot)
    pilot.run = ROOT/'replay'
    pilot.config = {**config, 'max_request_hops': 1}
    pilot.broker = InquiryBroker(CASE, pilot.run/'services', config, planner=None,
                                fetch=lambda _: (_ for _ in ()).throw(AssertionError('No online retrieval')))
    received = {}

    def receive(stage, researcher, task, context, notes=False):
        received[stage] = context
        save(pilot.run/'mock_returns'/(stage+'.json'), context)
        return {'learning_request': {'needed': False}}

    pilot.call = receive
    original = CASE/'runs/inquiry_v2_live_20261106_002'
    outcomes = []
    for source in sorted(original.glob('stages/*/result.json')):
        answer = load(source)
        if not answer.get('analysis_plan'):
            continue
        stage = 'replay_'+source.parent.name
        # Isolate the actual plan, without repeating historical literature requests.
        supplied = {'analysis_plan': answer['analysis_plan'], 'learning_request': {'needed': False}}
        pilot.service(stage, 'test_receiver', supplied)
        reply = received[stage+'_learn_0']['broker_reply']
        computation = reply['computed'][0]
        assert computation['request'] == answer['analysis_plan']
        status = computation['result']['status']
        assert status in {'executed', 'pending_controller'}
        outcomes.append({'original_result': str(source), 'original_sha256': digest(source),
                         'stage': source.parent.name, 'status': status,
                         'pending_reason': computation['result'].get('capability_task', {}).get('reason'),
                         'returned_to_mock_receiver': True})

    assert len(outcomes) == 8
    plan = load(original/'stages/01_initial_0/result.json')['analysis_plan']
    result = received['replay_01_initial_0_learn_0']['broker_reply']['computed'][0]['result']
    positions, _ = pilot.broker.arrays(plan['record_id'])
    positions = positions[plan['start']:plan['stop']]
    distance = np.sqrt(np.sum((positions[:, 0, :] - positions[:, 1, :])**2, axis=1))
    future = np.full(len(distance), np.nan)
    future[:-10] = distance[10:] - distance[:-10]
    actual = np.load(result['full_outputs'])
    np.testing.assert_allclose(actual['output_0'], distance, equal_nan=True)
    np.testing.assert_allclose(actual['output_1'], future, equal_nan=True)
    valid = np.isfinite(distance) & np.isfinite(future)
    masks = [valid & (distance <= np.quantile(distance, .25)),
             valid & (distance >= np.quantile(distance, .75))]
    for group, mask in zip(result['groups'], masks):
        assert group['selected_rows'] == int(mask.sum())
        np.testing.assert_allclose(group['values']['future_change_10']['mean'], future[mask].mean())
    x = np.column_stack([np.ones(len(distance)), distance])
    train = valid & (np.arange(len(distance)) < int(len(distance)*.7))
    coef = np.linalg.lstsq(x[train], future[train], rcond=None)[0]
    # Public JSON summaries use clean(...), which rounds floats to seven decimals.
    np.testing.assert_allclose(result['model']['coefficients'], coef, rtol=0, atol=5e-8)
    report = {'historical_researcher_resumed': False, 'live_model_calls': 0,
              'plan_content_changed': False, 'independent_numpy_check': 'passed',
              'coefficient_summary_absolute_tolerance': 5e-8,
              'executed': sum(o['status'] == 'executed' for o in outcomes),
              'pending_with_explicit_reason': sum(o['status'] == 'pending_controller' for o in outcomes),
              'outcomes': outcomes}
    save(ROOT/'REPLAY_RESULTS.json', report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
