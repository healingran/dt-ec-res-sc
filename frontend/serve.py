"""
本地静态页服务（替代 `python -m http.server`）。

Windows 下默认 http.server 常把 .js 标成 text/plain，浏览器对 type=module
会拒绝加载。此处强制为 application/javascript。
"""

from __future__ import annotations

import http.server
import socketserver
from pathlib import Path

FRONTEND_DIR = Path(__file__).resolve().parent
PORT = 8080

_ext = dict(http.server.SimpleHTTPRequestHandler.extensions_map)
_ext.update(
    {
        ".js": "application/javascript",
        ".mjs": "application/javascript",
        ".json": "application/json; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".html": "text/html; charset=utf-8",
        ".svg": "image/svg+xml",
    }
)


class FrontendHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    extensions_map = _ext

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)

    def log_message(self, fmt: str, *args) -> None:
        print(f"[frontend] {self.address_string()} - {fmt % args}")


def main() -> None:
    with socketserver.TCPServer(("127.0.0.1", PORT), FrontendHTTPRequestHandler) as httpd:
        print(f"Serving {FRONTEND_DIR}")
        print(f"Open: http://127.0.0.1:{PORT}/dashboard.html")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
