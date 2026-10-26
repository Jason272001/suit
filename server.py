"""Local-only web application. Run with .venv/Scripts/python.exe server.py."""
import base64
import binascii
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

from main import capture_issue, estimate_measurements

WEB = Path(__file__).parent / 'web'
MAX_BODY = 12 * 1024 * 1024
detector_lock = threading.Lock()
detector = None


def detect_image(encoded):
    import cv2
    import mediapipe as mp
    import numpy as np
    global detector
    raw = base64.b64decode(encoded, validate=True)
    # Reject excessive dimensions before allocating the decoded raster.
    from PIL import Image
    from io import BytesIO
    with Image.open(BytesIO(raw)) as header:
        if header.width * header.height > 16_000_000:
            raise ValueError('Photo too large. Use a photo under 16 megapixels.')
    image = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError('Cannot read photo. Use a JPEG or PNG image.')
    height, width = image.shape[:2]
    with detector_lock:
        if detector is None:
            detector = mp.solutions.pose.Pose(static_image_mode=True, model_complexity=1,
                                               min_detection_confidence=0.7)
        result = detector.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    points = result.pose_landmarks.landmark if result.pose_landmarks else None
    issue = capture_issue(points)
    if issue:
        raise ValueError(issue + '. Retake facing the camera with head, hands and feet visible.')
    return {'width': width, 'height': height,
            'points': [{'x': p.x, 'y': p.y, 'visibility': p.visibility} for p in points]}


class Handler(BaseHTTPRequestHandler):
    def reply(self, status, value):
        body = json.dumps(value, allow_nan=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        paths = {'/': ('index.html', 'text/html; charset=utf-8'),
                 '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
                 '/style.css': ('style.css', 'text/css; charset=utf-8')}
        if self.path == '/api/health':
            return self.reply(200, {'status': 'ok'})
        if self.path not in paths:
            return self.reply(404, {'error': 'Not found'})
        name, mime = paths[self.path]
        body = (WEB / name).read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; img-src 'self' blob: data:; media-src 'self' blob:; style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        # No CORS; reject browser requests originating outside this local app.
        if self.headers.get('Origin') not in (None, 'http://127.0.0.1:8765', 'http://localhost:8765'):
            return self.reply(403, {'error': 'Use the local application address.'})
        if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
            return self.reply(415, {'error': 'Expected application/json'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= MAX_BODY:
                return self.reply(413, {'error': 'Request too large or empty. Choose a smaller photo.'})
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError('Invalid request')
            if self.path == '/api/detect':
                result = detect_image(data['image'])
            elif self.path == '/api/measure':
                points = [SimpleNamespace(**p) for p in data['points']]
                result = {'estimates': estimate_measurements(
                    points, data['width'], data['height'], data['height_inches'],
                    data['crown'], data['floor'])}
            else:
                return self.reply(404, {'error': 'Not found'})
            self.reply(200, result)
        except (ValueError, TypeError, KeyError, AttributeError, binascii.Error, OSError) as exc:
            self.reply(400, {'error': str(exc) or 'Invalid request'})
        except Exception:
            self.reply(500, {'error': 'Image processing failed. Check server dependencies and try again.'})


if __name__ == '__main__':
    server = ThreadingHTTPServer(('127.0.0.1', 8765), Handler)
    print('Suit Studio ready at http://127.0.0.1:8765', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        if detector is not None:
            detector.close()
