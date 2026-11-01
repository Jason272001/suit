import copy
import unittest
from types import SimpleNamespace

from calibration import resolve_height
from server import measure


class ReferenceCalibrationTests(unittest.TestCase):
    def setUp(self):
        self.points = [dict(x=0.5, y=0.5, visibility=0.99) for _ in range(33)]
        self.points[0]['y'] = 0.15
        for left, right, y in ((11, 12, 0.3), (23, 24, 0.5), (25, 26, 0.7), (27, 28, 0.87), (29, 30, 0.89)):
            self.points[left].update(x=0.4, y=y)
            self.points[right].update(x=0.6, y=y)
        self.data = dict(points=self.points, width=1000, height=1000, crown=100, floor=900,
                         height_source='reference', height_inches=None,
                         reference=dict(length_cm=29.7, setup_confirmed=True,
                                        top=dict(x=200, y=400),
                                        bottom=dict(x=200, y=400 + 800 * 29.7 / (72 * 2.54))))

    def resolve(self, data=None):
        data = data or self.data
        return resolve_height(data, [SimpleNamespace(**p) for p in data['points']])

    def test_unknown_height_resolved_from_reference(self):
        result = measure(self.data)
        self.assertAlmostEqual(result['height']['inches'], 72)
        self.assertIsNone(result['height']['entered_inches'])
        self.assertFalse(result['height']['verified'])
        self.assertFalse(result['production_ready'])
        self.assertAlmostEqual(result['estimates']['shoulder_landmark_span'], 18)

    def test_wrong_height_does_not_rescale_results(self):
        self.data['height_inches'] = 84
        result = measure(self.data)
        self.assertAlmostEqual(result['height']['inches'], 72)
        self.assertEqual(result['height']['status'], 'height_conflict')
        self.assertIsNone(result['estimates'])
        self.assertTrue(result['height']['comparison']['conflict'])

    def test_one_inch_boundary_and_small_discrepancy(self):
        for entered, conflict in ((71, True), (73, True), (71.01, False), (72.99, False)):
            self.data['height_inches'] = entered
            with self.subTest(entered=entered):
                self.assertEqual(self.resolve()['comparison']['conflict'], conflict)
                self.assertAlmostEqual(self.resolve()['inches'], 72)

    def test_reference_geometry_rejects_small_tilted_reversed_and_outside(self):
        for bottom in (dict(x=200, y=420), dict(x=300, y=530), dict(x=200, y=300), dict(x=1001, y=530), dict(x=200, y=950)):
            with self.subTest(bottom=bottom), self.assertRaises(ValueError):
                data = copy.deepcopy(self.data)
                data['reference']['bottom'] = bottom
                self.resolve(data)

    def test_missing_scale_cannot_be_guessed(self):
        for key, value in (('reference', None), ('height_source', 'ai_guess'), ('width', float('nan'))):
            with self.subTest(key=key), self.assertRaises((ValueError, TypeError)):
                data = copy.deepcopy(self.data)
                data[key] = value
                self.resolve(data)
        self.data['reference']['setup_confirmed'] = False
        with self.assertRaises(ValueError):
            self.resolve()

    def test_unrealistic_height_and_reference_length_rejected(self):
        for length in (0, True, float('nan'), 201, 100):
            with self.subTest(length=length), self.assertRaises(ValueError):
                data = copy.deepcopy(self.data)
                data['reference']['length_cm'] = length
                self.resolve(data)

    def test_leaning_and_side_views_rejected(self):
        self.points[23]['x'] = self.points[24]['x'] = 0.8
        with self.assertRaisesRegex(ValueError, 'leaning'):
            self.resolve()
        self.points[23]['x'] = self.points[24]['x'] = 0.5
        self.points[11]['x'] = 0.49
        self.points[12]['x'] = 0.51
        with self.assertRaisesRegex(ValueError, 'Face the camera'):
            self.resolve()

    def test_uniform_image_resize_does_not_change_height(self):
        resized = copy.deepcopy(self.data)
        for key in ('width', 'height', 'crown', 'floor'):
            resized[key] *= 2
        for endpoint in ('top', 'bottom'):
            for axis in ('x', 'y'):
                resized['reference'][endpoint][axis] *= 2
        self.assertAlmostEqual(self.resolve()['inches'], self.resolve(resized)['inches'])

    def test_entered_mode_is_explicitly_unverified(self):
        self.data.update(height_source='entered', height_inches=68)
        result = self.resolve()
        self.assertEqual(result['inches'], 68)
        self.assertFalse(result['verified'])
        self.assertIsNone(result['reference'])


if __name__ == '__main__':
    unittest.main()
