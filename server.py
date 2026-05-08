#!/usr/bin/env python3
"""
AI News Server - 本地服务器，支持选择不同日期查看新闻
"""

import http.server
import json
import os
import socketserver
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from generate_page import generate_html, load_news_by_date, get_available_dates

# 配置
SCRIPT_DIR = Path(__file__).parent.resolve()
DATA_DIR = SCRIPT_DIR / "data"
DEFAULT_PORT = 8080

# MIME 类型
MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
}


class NewsHandler(http.server.SimpleHTTPRequestHandler):
    """自定义 HTTP 处理"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SCRIPT_DIR), **kwargs)

    def do_GET(self):
        """处理 GET 请求"""
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        query = parsed.query

        if path == "/" or path == "/index.html":
            # 首页：重定向到最新可用日期
            dates = get_available_dates(DATA_DIR)
            if dates:
                latest = dates[-1]
                self.send_response(302)
                self.send_header("Location", f"/date/{latest}")
                self.end_headers()
            else:
                self._serve_no_data()
            return

        if path.startswith("/date/"):
            # 特定日期的页面
            date_str = path.split("/")[-1]
            self._serve_date_page(date_str)
            return

        if path == "/api/dates":
            # API: 返回所有可用日期列表
            dates = get_available_dates(DATA_DIR)
            self._serve_json({"dates": dates})
            return

        if path.startswith("/api/news/"):
            # API: 返回指定日期的新闻 JSON
            date_str = path.split("/")[-1]
            news, data_date = load_news_by_date(date_str, DATA_DIR)
            if news:
                self._serve_json({"date": data_date, "news": news, "count": len(news)})
            else:
                self._serve_json(
                    {"error": "No data for this date", "available": get_available_dates(DATA_DIR)},
                    status=404
                )
            return

        # 静态文件
        return super().do_GET()

    def _serve_date_page(self, date_str):
        """为指定日期生成并返回 HTML"""
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            self._serve_error(400, "Invalid date format. Use YYYY-MM-DD")
            return

        dates = get_available_dates(DATA_DIR)
        news, data_date = load_news_by_date(date_str, DATA_DIR)
        if not news:
            self._serve_no_data(date_str, dates)
            return

        html = generate_html(news, data_date, dates)
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _serve_no_data(self, requested_date=None, available=None):
        """返回无数据提示页"""
        if available is None:
            available = get_available_dates(DATA_DIR)
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI News Daily</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0a0a0f; color: #e0e0e0; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }}
        .box {{ text-align: center; padding: 40px; background: #12121a; border: 1px solid #2a2a3a; border-radius: 16px; max-width: 500px; }}
        h1 {{ font-size: 1.5em; margin-bottom: 20px; color: #667eea; }}
        p {{ color: #888; margin-bottom: 16px; }}
        code {{ background: #1a1a2e; padding: 2px 8px; border-radius: 4px; color: #667eea; }}
    </style>
</head>
<body>
    <div class="box">
        <h1>📭 暂无新闻数据</h1>
        <p>没有找到指定日期的新闻。运行抓取命令：</p>
        <p><code>python3 fetch_news.py</code></p>
        {('<p style="margin-top:20px">可用日期：' + ', '.join(available) + '</p>') if available else ''}
    </div>
</body>
</html>"""
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _serve_json(self, data, status=200):
        """返回 JSON"""
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _serve_error(self, code, msg):
        """返回错误页"""
        html = f"<!DOCTYPE html><html><head><meta charset='UTF-8'><title>{code}</title></head><body style='background:#0a0a0f;color:#e0e0e0;display:flex;justify-content:center;align-items:center;height:100vh;font-family:sans-serif;'><h1 style='font-size:3em;margin:0'>{code}</h1><p style='color:#888'>{msg}</p></body></html>"
        body = html.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def guess_type(self, path):
        """MIME 类型猜测"""
        ext = os.path.splitext(path)[1].lower()
        return MIME_TYPES.get(ext, "application/octet-stream")

    def log_message(self, format, *args):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]}")


def get_free_port(start=8080):
    """找一个可用端口"""
    import socket
    port = start
    while port < start + 100:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            port += 1
    raise RuntimeError("No available port found")


def get_lan_ip():
    """获取局域网 IP"""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"


def start_server(port=None):
    """启动服务器"""
    if port is None:
        port = DEFAULT_PORT

    # 检查端口是否可用，不行就找下一个
    import socket
    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("0.0.0.0", port))
            break
        except OSError:
            print(f"⚠ 端口 {port} 已被占用，尝试 {port + 1} ...")
            port += 1

    with socketserver.TCPServer(("0.0.0.0", port), NewsHandler) as httpd:
        lan_ip = get_lan_ip()
        print("=" * 50)
        print("🤖 AI News Server 启动成功！")
        print("=" * 50)
        print(f"🌐 局域网访问: http://{lan_ip}:{port}")
        print(f"🔒 本地访问:   http://localhost:{port}")
        print(f"📅 新闻日期:   http://localhost:{port}/date/2026-05-08")
        print("")
        print("按 Ctrl+C 停止服务器")
        print("=" * 50)
        httpd.serve_forever()


if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT
    start_server(port)
