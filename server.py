"""Dependency-free measurement API and local web preview server."""
import json
import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit

from main import estimate_measurements

WEB = Path(__file__).parent / 'web'
MAX_BODY = 64 * 1024
CSP = ("default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; "
       "img-src 'self' blob: data:; media-src 'self' blob:; style-src 'self'; "
       "connect-src 'self'; worker-src 'self' blob:; frame-ancestors 'none'")


def measure(data):
    if not isinstance(data, dict):
        raise ValueError('Expected a JSON object.')
    points = data['points']
    if not isinstance(points, list) or len(points) != 33:
        raise ValueError('Expected exactly 33 body landmarks.')
    points = [SimpleNamespace(x=p['x'], y=p['y'], visibility=p['visibility']) for p in points]
    for key in ('width', 'height', 'height_inches', 'crown', 'floor'):
        value = data[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f'{key} must be a number.')
    return {'estimates': estimate_measurements(
        points, data['width'], data['height'], data['height_inches'],
        data['crown'], data['floor'])}


class Handler(BaseHTTPRequestHandler):
    def reply(self, status, value):
        body = json.dumps(value, allow_nan=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == '/api/health':
            return self.reply(200, {'status': 'ok', 'inference': 'browser'})
        if path.startswith('/api/'):
            return self.reply(404, {'error': 'Not found'})
        file = (WEB / (path.lstrip('/') or 'index.html')).resolve()
        if not file.is_relative_to(WEB.resolve()) or not file.is_file():
            return self.reply(404, {'error': 'Not found'})
        body = file.read_bytes()
        mime = {'.mjs': 'text/javascript', '.js': 'text/javascript',
                '.wasm': 'application/wasm', '.task': 'application/octet-stream'}.get(file.suffix)
        mime = mime or mimetypes.guess_type(str(file))[0] or 'application/octet-stream'
        self.send_response(200)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', CSP)
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        origin = self.headers.get('Origin')
        host = self.headers.get('Host')
        if origin:
            parsed = urlsplit(origin)
            if parsed.scheme not in ('http', 'https') or parsed.netloc != host:
                return self.reply(403, {'error': 'Use this application from its own website.'})
        if urlsplit(self.path).path != '/api/measure':
            return self.reply(404, {'error': 'Not found'})
        if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
            return self.reply(415, {'error': 'Expected application/json'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= MAX_BODY:
                return self.reply(413, {'error': 'Send landmarks only; images are processed in your browser.'})
            data = json.loads(self.rfile.read(length))
            self.reply(200, measure(data))
        except (ValueError, TypeError, KeyError, AttributeError, OverflowError) as exc:
            self.reply(400, {'error': str(exc) or 'Invalid request'})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', '8765'))
    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    print(f'Suit Studio ready at http://127.0.0.1:{port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
