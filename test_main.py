import json
import tempfile
import unittest
from types import SimpleNamespace

from main import capture_issue, estimate_measurements, parse_height, save_report


class MeasurementTests(unittest.TestCase):
    def setUp(self):
        self.points = [SimpleNamespace(x=0.5, y=0.5, visibility=0.99) for _ in range(33)]
        self.points[0].y = 0.15
        self.points[29].y = self.points[30].y = 0.88
        self.points[11].x, self.points[12].x = 0.4, 0.6

    def test_invalid_height_never_defaults(self):
        for raw in ('', 'nan', 'inf', '-1', '0', '101', 'abc'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                parse_height(raw)

    def test_quality_rejects_hidden_clipped_and_invalid_points(self):
        for attribute, value in (('visibility', 0.2), ('x', 1.1), ('y', float('nan'))):
            old = getattr(self.points[11], attribute)
            setattr(self.points[11], attribute, value)
            self.assertIsNotNone(capture_issue(self.points))
            setattr(self.points[11], attribute, old)
        self.assertIsNotNone(capture_issue(None))

    def test_calibration_and_scale(self):
        values = estimate_measurements(self.points, 1000, 1000, 72, 100, 900)
        self.assertAlmostEqual(values['shoulder_landmark_span'], 18)
        doubled = estimate_measurements(self.points, 2000, 2000, 72, 200, 1800)
        self.assertEqual(values, doubled)
        self.assertFalse(any('circumference' in key or 'inseam' in key for key in values))

    def test_bad_calibration_rejected(self):
        for crown, floor in ((900, 100), (100, 200), (200, 900), (100, 850), (float('nan'), 900)):
            with self.subTest(crown=crown, floor=floor), self.assertRaises(ValueError):
                estimate_measurements(self.points, 1000, 1000, 72, crown, floor)

    def test_reports_preserve_previous_session_and_mark_limitations(self):
        with tempfile.TemporaryDirectory() as folder:
            first = save_report({'shoulder_landmark_span': 18}, 72, folder)
            second = save_report({}, 72, folder)
            self.assertNotEqual(first, second)
            report = json.loads(first.read_text())
            self.assertEqual(report['units'], 'inches')
            self.assertIn('inseam', report['requires_manual_measurement'])
            self.assertEqual(report['status'], 'unvalidated_landmark_estimates')


if __name__ == '__main__':
    unittest.main()
