

import functools
import http.server
import socketserver
import threading

_state = {"httpd": None, "url": None}
_lock = threading.Lock()


class _NoCacheHandler(http.server.SimpleHTTPRequestHandler):

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        super().end_headers()

    def log_message(self, format, *args):
        pass  # keep the console quiet


def ensure_server(directory, preferred_port=8877, port_range=40):
    with _lock:
        if _state["httpd"] is not None:
            return _state["url"]

        handler_cls = functools.partial(_NoCacheHandler, directory=directory)

        last_error = None
        for port in range(preferred_port, preferred_port + port_range):
            try:
                httpd = socketserver.TCPServer(("127.0.0.1", port), handler_cls)
                break
            except OSError as e:
                last_error = e
                httpd = None
        if httpd is None:
            raise RuntimeError(f"Could not bind a preview server port: {last_error}")

        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()

        _state["httpd"] = httpd
        _state["url"] = f"http://127.0.0.1:{port}"
        return _state["url"]
