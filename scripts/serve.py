"""
支持 HTTP Range 请求的静态文件服务（python -m http.server 不支持 Range，
导致 video 元素 seek 失效——这是 study.html 跳转一直失败的根因）。

用法：python scripts/serve.py [port]
"""
import os
import re
import sys
import http.server
import socketserver
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class RangeRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        path = self.translate_path(self.path)
        range_header = self.headers.get("Range")

        if not range_header or not os.path.isfile(path):
            return super().do_GET()

        m = re.match(r"bytes=(\d+)-(\d*)", range_header)
        if not m:
            return super().do_GET()

        try:
            size = os.path.getsize(path)
        except OSError:
            return super().do_GET()

        start = int(m.group(1))
        end = int(m.group(2)) if m.group(2) else size - 1
        if end >= size:
            end = size - 1
        if start > end or start >= size:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            self.end_headers()
            return

        length = end - start + 1
        ctype = self.guess_type(path)

        self.send_response(206)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(length))
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        try:
            with open(path, "rb") as f:
                f.seek(start)
                remaining = length
                while remaining > 0:
                    chunk = f.read(min(64 * 1024, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def end_headers(self):
        # 让 HEAD / 全量 GET 也声明支持 Range，浏览器才知道可以 seek
        self.send_header("Accept-Ranges", "bytes")
        super().end_headers()


def main() -> int:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8008
    os.chdir(PROJECT_ROOT)
    # 复用地址 + IPv4 only（Windows 上 IPv6 偶尔有怪问题）
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", port), RangeRequestHandler) as httpd:
        print(f"[serve] http://localhost:{port}  (Range-aware) serving {PROJECT_ROOT}", flush=True)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[serve] stopped", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
