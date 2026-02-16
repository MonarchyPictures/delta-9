
import http.server
import http.client
import socketserver

PORT = 8001
TARGET = "localhost"
TARGET_PORT = 8000

class ProxyHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.proxy_request()

    def do_POST(self):
        self.proxy_request()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "X-API-Key, Content-Type")
        self.end_headers()

    def proxy_request(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else None

        conn = http.client.HTTPConnection(TARGET, TARGET_PORT)
        
        headers = {key: value for key, value in self.headers.items() if key.lower() != 'host'}
        
        conn.request(self.command, self.path, body, headers)
        res = conn.getresponse()

        self.send_response(res.status)
        for key, value in res.getheaders():
            if key.lower() != 'transfer-encoding':
                self.send_header(key, value)
        
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(res.read())

with socketserver.TCPServer(("", PORT), ProxyHandler) as httpd:
    print(f"Proxying from {PORT} to {TARGET_PORT} with CORS enabled")
    httpd.serve_forever()
