import unittest
from evaluate_height import evaluate


class EvaluationTests(unittest.TestCase):
    def test_absolute_error_bias_and_repeatability(self):
        records = [dict(subject_id='a', estimated_cm=171, measured_cm=170, ground_truth_method='stadiometer'),
                   dict(subject_id='a', estimated_cm=169, measured_cm=170, ground_truth_method='stadiometer'),
                   dict(subject_id='b', estimated_cm=174, measured_cm=170, ground_truth_method='wall_and_tape')]
        result = evaluate(records)
        self.assertEqual(result['mean_absolute_error_cm'], 2)
        self.assertEqual(result['mean_repeat_range_cm'], 2)
        self.assertEqual(result['subject_count'], 2)
        self.assertEqual(result['p95_absolute_error_cm'], 4)
        self.assertFalse(result['production_ready'])

    def test_self_reported_or_missing_ground_truth_rejected(self):
        for records in ([], [dict(subject_id='a', estimated_cm=171, measured_cm=170, ground_truth_method='self_reported')]):
            with self.assertRaises(ValueError):
                evaluate(records)
