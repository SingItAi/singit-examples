import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
import pytest


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    original_resolve = socket.getaddrinfo
    def resolve(host, *args, **kwargs):
        if host != "127.0.0.1":
            raise AssertionError("Offline test blocked non-loopback DNS")
        return original_resolve(host, *args, **kwargs)
    monkeypatch.setattr(socket, "getaddrinfo", resolve)
    original = socket.socket.connect
    def connect(sock, address):
        if isinstance(address, tuple) and address[0] != "127.0.0.1":
            raise AssertionError("Offline test blocked a non-loopback connection")
        return original(sock, address)
    monkeypatch.setattr(socket.socket, "connect", connect)
    original_ex = socket.socket.connect_ex
    def connect_ex(sock, address):
        if isinstance(address, tuple) and address[0] != "127.0.0.1":
            raise AssertionError("Offline test blocked a non-loopback connection")
        return original_ex(sock, address)
    monkeypatch.setattr(socket.socket, "connect_ex", connect_ex)
    monkeypatch.setenv("LITELLM_LOCAL_MODEL_COST_MAP", "True")
    monkeypatch.setenv("NO_PROXY", "127.0.0.1")


@pytest.fixture
def server():
    state = SimpleNamespace(requests=[], replies=[])
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            state.requests.append((self.path, self.headers, body))
            status, payload, headers = state.replies.pop(0)
            self.send_response(status)
            for k, v in headers.items():
                self.send_header(k, v)
            self.send_header("Content-Type", "text/event-stream" if isinstance(payload, str) else "application/json")
            self.end_headers()
            self.wfile.write(payload.encode() if isinstance(payload, str) else json.dumps(payload).encode())
            self.wfile.flush()
            self.close_connection = True
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    state.url = "http://127.0.0.1:" + str(httpd.server_port)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield state
    httpd.shutdown()
    httpd.server_close()
    thread.join(timeout=5)
