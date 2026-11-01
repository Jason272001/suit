import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from server import Handler


class WebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = 'http://127.0.0.1:' + str(cls.server.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def post(self, path, data, origin=None):
        headers = {'Content-Type': 'application/json'}
        if origin:
            headers['Origin'] = origin
        request = Request(self.url + path, data=json.dumps(data).encode(), headers=headers)
        try:
            response = urlopen(request)
        except HTTPError as error:
            response = error
        with response:
            return response.status, json.load(response)

    def test_page_assets_and_health(self):
        for path in ('/', '/app.js', '/detector.js', '/style.css', '/api/health'):
            with self.subTest(path=path), urlopen(self.url + path) as response:
                self.assertEqual(response.status, 200)
                self.assertTrue(response.read())

    def test_measurement_endpoint(self):
        points = [dict(x=0.5, y=0.5, visibility=0.99) for _ in range(33)]
        points[0]['y'] = 0.15
        points[29]['y'] = points[30]['y'] = 0.88
        points[11]['x'], points[12]['x'] = 0.4, 0.6
        data = dict(points=points, width=1000, height=1000, height_inches=72, crown=100, floor=900)
        status, result = self.post('/api/measure', data)
        self.assertEqual(status, 200)
        self.assertAlmostEqual(result['estimates']['shoulder_landmark_span'], 18)
        data['height_inches'] = 0
        self.assertEqual(self.post('/api/measure', data)[0], 400)

    def test_invalid_requests_and_external_origin(self):
        self.assertEqual(self.post('/api/measure', {})[0], 400)
        self.assertEqual(self.post('/api/detect', {'image': 'not base64!'})[0], 404)
        self.assertEqual(self.post('/api/measure', {}, 'https://example.com')[0], 403)
        self.assertEqual(self.post('/api/nope', {})[0], 404)

    def test_reference_height_conflict_through_http(self):
        from test_calibration import ReferenceCalibrationTests
        fixture = ReferenceCalibrationTests()
        fixture.setUp()
        status, result = self.post('/api/measure', fixture.data)
        self.assertEqual(status, 200)
        self.assertAlmostEqual(result['height']['inches'], 72)
        fixture.data['height_inches'] = 73
        status, result = self.post('/api/measure', fixture.data)
        self.assertEqual(status, 200)
        self.assertEqual(result['height']['status'], 'height_conflict')
        self.assertIsNone(result['estimates'])

    def test_same_origin_requests_and_landmark_payload_limit(self):
        # An accepted origin reaches input validation, including hosted HTTPS.
        self.assertEqual(self.post('/api/measure', {}, self.url)[0], 400)
        self.assertEqual(self.post('/api/measure', {}, self.url.replace('http:', 'https:'))[0], 400)
        status, result = self.post('/api/measure', {'image': 'x' * 70_000})
        self.assertEqual(status, 413)
        self.assertIn('landmarks only', result['error'])

    def test_static_asset_types_and_traversal(self):
        with urlopen(self.url + '/vendor/wasm/vision_wasm_internal.wasm') as response:
            self.assertEqual(response.headers['Content-Type'], 'application/wasm')
        with self.assertRaises(HTTPError) as error:
            urlopen(self.url + '/../main.py')
        self.assertEqual(error.exception.code, 404)

    def test_vercel_entry_points_import_without_camera_libraries(self):
        from api.measure import handler as measurement_handler
        from api.health import handler as health_handler
        self.assertTrue(issubclass(measurement_handler, Handler))
        self.assertTrue(issubclass(health_handler, Handler))


if __name__ == '__main__':
    unittest.main()
