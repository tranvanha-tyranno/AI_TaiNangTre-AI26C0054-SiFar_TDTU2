import unittest
from scripts.compare_baseline import compare


class PairedEvaluationTest(unittest.TestCase):
    def test_reports_gains_and_regressions_even_when_score_ties(self):
        result = compare({'a':'1','b':'0','c':'3','d':''},
                         {'a':'0','b':'2','c':'3','d':''},
                         {'a':'1','b':'2','c':'3','d':'4'})
        self.assertEqual(result['questions'], {'both_correct':['c'], 'gained':['b'],
                                             'regressed':['a'], 'both_wrong':['d']})
        self.assertEqual(result['net_gain'], 0)

    def test_partial_or_extra_ids_rejected(self):
        for prediction in ({}, {'a':'1','extra':'2'}):
            with self.assertRaises(ValueError):
                compare({'a':'1'}, prediction, {'a':'1'})
