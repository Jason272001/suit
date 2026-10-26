import base64
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
        for path in ('/', '/app.js', '/style.css', '/api/health'):
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
        self.assertEqual(self.post('/api/detect', {'image': 'not base64!'})[0], 400)
        self.assertEqual(self.post('/api/measure', {}, 'https://example.com')[0], 403)
        self.assertEqual(self.post('/api/nope', {})[0], 404)

    def test_no_body_photo_rejected(self):
        import cv2
        import numpy as np
        success, image = cv2.imencode('.jpg', np.zeros((480, 640, 3), dtype=np.uint8))
        self.assertTrue(success)
        status, result = self.post('/api/detect', {'image': base64.b64encode(image).decode()})
        self.assertEqual(status, 400)
        self.assertIn('Full body not detected', result['error'])


if __name__ == '__main__':
    unittest.main()
