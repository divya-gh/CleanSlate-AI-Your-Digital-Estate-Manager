"""Reverse-proxy launcher for CleanSlate AI.

Runs on http://127.0.0.1:8001 and:
  - Serves launcher.html for GET /
  - Forwards every other request to the ADK backend (port 8000) verbatim,
    including streaming SSE responses for /run_sse.

This eliminates CORS entirely: the browser only ever talks to port 8001.

Usage:
    python launcher_server.py
"""

import http.client
import http.server
import pathlib

LAUNCHER_PORT  = 8001
BACKEND_HOST   = "127.0.0.1"
BACKEND_PORT   = 8000
ROOT           = pathlib.Path(__file__).parent

# Headers we must not forward blindly (hop-by-hop)
_HOP_BY_HOP = frozenset([
    "connection", "keep-alive", "proxy-authenticate",
    "proxy-authorization", "te", "trailers",
    "transfer-encoding", "upgrade",
])


class ReverseProxyHandler(http.server.BaseHTTPRequestHandler):
    # ------------------------------------------------------------------ #
    #  Serve the launcher HTML for the root path                         #
    # ------------------------------------------------------------------ #
    def do_GET(self):
        if self.path in ("/", "", "/launcher.html"):
            self._serve_html()
        else:
            self._proxy("GET", body=None)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body   = self.rfile.read(length) if length > 0 else b""
        self._proxy("POST", body=body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    # ------------------------------------------------------------------ #
    #  Serve launcher.html                                               #
    # ------------------------------------------------------------------ #
    def _serve_html(self):
        html_path = ROOT / "launcher.html"
        if not html_path.exists():
            self.send_error(404, "launcher.html not found")
            return
        content = html_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    # ------------------------------------------------------------------ #
    #  Proxy any other request to ADK backend, streaming SSE             #
    # ------------------------------------------------------------------ #
    def _proxy(self, method: str, body):
        forward_headers = {
            k: v for k, v in self.headers.items()
            if k.lower() not in _HOP_BY_HOP and k.lower() != "host"
        }
        if body:
            forward_headers["Content-Length"] = str(len(body))

        conn = http.client.HTTPConnection(BACKEND_HOST, BACKEND_PORT, timeout=300)
        try:
            conn.request(method, self.path, body=body, headers=forward_headers)
            resp = conn.getresponse()

            # Forward status + headers
            self.send_response(resp.status)
            for key, val in resp.getheaders():
                if key.lower() not in _HOP_BY_HOP:
                    self.send_header(key, val)
            self._cors_headers()
            self.end_headers()

            # Stream the body (critical for SSE)
            while True:
                chunk = resp.read(512)
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    break

        except ConnectionRefusedError:
            self.send_error(
                502,
                "ADK backend unreachable. "
                "Make sure `adk web agents` is running on port 8000.",
            )
        except Exception as exc:
            try:
                self.send_error(502, str(exc))
            except Exception:
                pass
        finally:
            conn.close()

    # ------------------------------------------------------------------ #
    #  CORS headers                                                      #
    # ------------------------------------------------------------------ #
    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    # ------------------------------------------------------------------ #
    #  Suppress access logs (keep terminal clean)                        #
    # ------------------------------------------------------------------ #
    def log_message(self, fmt, *args):  # noqa: ARG002
        pass


# ------------------------------------------------------------------ #
#  Entry point                                                         #
# ------------------------------------------------------------------ #
if __name__ == "__main__":
    addr = ("127.0.0.1", LAUNCHER_PORT)
    with http.server.HTTPServer(addr, ReverseProxyHandler) as srv:
        print(f"CleanSlate AI launcher  ->  http://127.0.0.1:{LAUNCHER_PORT}")
        print(f"ADK backend             ->  http://127.0.0.1:{BACKEND_PORT}")
        print("Press Ctrl+C to stop.")
        srv.serve_forever()
