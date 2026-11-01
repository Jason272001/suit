from server import Handler


class handler(Handler):
    def do_GET(self):
        self.path = '/api/health'
        super().do_GET()
