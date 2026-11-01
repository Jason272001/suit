"""Vercel measurement endpoint: no image-processing dependencies."""
from server import Handler


class handler(Handler):
    def do_POST(self):
        self.path = '/api/measure'
        super().do_POST()
