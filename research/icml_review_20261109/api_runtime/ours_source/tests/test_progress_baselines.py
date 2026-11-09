"""Actual false-progress regression: a seed-only comparison overlooked supplied peer drafts."""
import copy
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from portfolio_contracts import validate_progress,progress_baselines


class BaselineTests(unittest.TestCase):
    def setUp(self):
        self.case=json.loads((Path(__file__).parent/'fixtures/progress_seed_only_real.json').read_text())

    def test_real_seed_only_positive_assessment_is_not_admitted(self):
        with self.assertRaisesRegex(ValueError,'baseline omits supplied groups'):
            validate_progress(self.case['result'],self.case['packet'])

    def test_each_actual_stage_exposes_immediate_baselines(self):
        for source in self.case['packet']['sources'].values():
            groups=progress_baselines(source)
            self.assertEqual(set(groups),{'current_self','peer_drafts','ranker_feedback','retrieved_memory'})
            supplied = json.dumps([groups['current_self'], groups['peer_drafts']],ensure_ascii=False)
            self.assertIn('评分映射',supplied)
            self.assertIn('评分分布',supplied)

    def test_uncertainty_is_allowed_without_manufacturing_progress(self):
        result=copy.deepcopy(self.case['result'])
        for c in result['changes']:
            c.update(classification='unclear',reason='Need comparison against supplied own and peer claims')
        validate_progress(result,self.case['packet'])


if __name__=='__main__':unittest.main()
