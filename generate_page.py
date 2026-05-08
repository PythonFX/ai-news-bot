#!/usr/bin/env python3
"""
AI News Page Generator - 生成静态 HTML 页面
"""

import json
import os
import re
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

from zoneinfo import ZoneInfo

# 配置
SCRIPT_DIR = Path(__file__).parent.resolve()
DATA_DIR = SCRIPT_DIR / "data"
OUTPUT_HTML = SCRIPT_DIR / "index.html"
TZ = ZoneInfo("Asia/Shanghai")


def load_news_by_date(date_str, data_dir=None):
    """根据日期加载新闻数据"""
    if data_dir is None:
        data_dir = DATA_DIR
    data_file = data_dir / f"news_{date_str}.json"

    if not data_file.exists():
        # 尝试找最新的数据文件
        if not data_dir.exists():
            return None, None
        files = sorted(data_dir.glob("news_*.json"))
        if files:
            data_file = files[-1]
        else:
            return None, None

    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["news"], data["date"]


def get_available_dates(data_dir=None):
    """获取所有有数据的日期列表"""
    if data_dir is None:
        data_dir = DATA_DIR
    if not data_dir.exists():
        return []
    files = sorted(data_dir.glob("news_*.json"))
    return [f.stem.replace("news_", "") for f in files]


def load_today_news():
    """加载今天的新闻数据（兼容旧接口）"""
    today = datetime.now(TZ).strftime("%Y-%m-%d")
    news, date = load_news_by_date(today, DATA_DIR)
    return news, date


ALLOWED_TAGS = {'b', 'strong', 'em', 'i', 'a'}


class SummaryHTMLParser(HTMLParser):
    """用 HTMLParser 正确处理摘要 HTML"""

    def __init__(self):
        super().__init__()
        self.result = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == 'a':
            attrs_dict = dict(attrs)
            href = attrs_dict.get('href', '#')
            self.result.append(f'<a href="{href}" target="_blank" rel="noopener">')
        elif tag in ALLOWED_TAGS:
            self.result.append(f'<{tag}>')

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in ALLOWED_TAGS:
            self.result.append(f'</{tag}>')

    def handle_data(self, data):
        self.result.append(data)

    def get_result(self):
        return ''.join(self.result)


def sanitize_html(html_text):
    """清理 HTML：保留粗体/斜体/链接，去掉其他标签但保留文本"""
    if not html_text:
        return ""

    # 去掉危险标签和脚本
    html_text = re.sub(r'<script[^>]*>.*?</script>', '', html_text, flags=re.DOTALL | re.IGNORECASE)
    html_text = re.sub(r'<style[^>]*>.*?</style>', '', html_text, flags=re.DOTALL | re.IGNORECASE)
    html_text = re.sub(r'on\w+\s*=\s*["\'][^"\']*["\']', '', html_text, flags=re.IGNORECASE)

    parser = SummaryHTMLParser()
    try:
        parser.feed(html_text)
    except:
        return html_text

    result = parser.get_result()
    # 清理连续空白
    result = re.sub(r'[ \t]+', ' ', result)
    return result.strip()


def escape_html(text):
    """HTML 转义"""
    if not text:
        return ""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;"))


def _build_date_picker(available_dates, current_date):
    """构建日期选择器 HTML"""
    if not available_dates:
        return ""

    dates_json = json.dumps(available_dates)
    options = []
    for d in sorted(available_dates):
        selected = 'selected' if d == current_date else ''
        label = d
        options.append(f'<option value="{d}" {selected}>{label}</option>')

    return f'''
    <div class="date-picker">
        <label for="date-select">📅 选择日期：</label>
        <select id="date-select" onchange="window.location.href='/date/' + this.value">
            {''.join(options)}
        </select>
    </div>
    '''


def generate_html(news_list, news_date, available_dates=None):
    """生成 HTML 页面"""

    # 按来源分组
    sources = {}
    for n in news_list:
        src = n.get("source", "Other")
        if src not in sources:
            sources[src] = []
        sources[src].append(n)

    # 日期选择器
    if available_dates is None:
        available_dates = [news_date] if news_date else []
    date_picker_html = _build_date_picker(available_dates, news_date)

    news_html = ""
    for source, items in sources.items():
        source_icons = {
            "Hacker News": "💻",
            "The Verge": "📰",
            "VentureBeat": "🚀",
            "TechCrunch": "💰",
            "Reuters": "🏛",
            "Ars Technica": "⚙️"
        }
        icon = source_icons.get(source, "📢")
        news_html += f'<div class="source-group"><h2 class="source-title">{icon} {escape_html(source)}</h2><div class="source-items">'

        for n in items:
            title = escape_html(n.get("title", ""))
            url = escape_html(n.get("url", "#"))
            summary_raw = n.get("summary", "")
            summary_html = sanitize_html(summary_raw)
            points = n.get("points", 0)
            comments = n.get("comments", 0)
            date = n.get("date", "")

            meta = []
            if points > 0:
                meta.append(f"⬆ {points}")
            if comments > 0:
                meta.append(f"💬 {comments}")
            if date:
                meta.append(f"📅 {date}")

            meta_str = ' <span class="separator">•</span> '.join(meta) if meta else ""

            news_html += f'''
        <div class="news-item">
            <h3 class="news-title"><a href="{url}" target="_blank" rel="noopener">{title}</a></h3>
            {f'<p class="news-summary">{summary_html}</p>' if summary_html else ''}
            {f'<div class="news-meta">{meta_str}</div>' if meta_str else ''}
        </div>'''

        news_html += "</div></div>"

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI News Daily - {news_date}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: #0a0a0f;
            color: #e0e0e0;
            min-height: 100vh;
            line-height: 1.6;
        }}
        .container {{ max-width: 900px; margin: 0 auto; padding: 40px 20px; }}
        header {{
            text-align: center;
            margin-bottom: 50px;
            padding: 40px 0;
            border-bottom: 1px solid #2a2a3a;
        }}
        h1 {{ font-size: 2.5em; font-weight: 700; margin-bottom: 10px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        .subtitle {{ color: #888; font-size: 1.1em; }}
        .stats {{ margin-top: 20px; display: flex; justify-content: center; gap: 30px; flex-wrap: wrap; }}
        .stat {{ text-align: center; }}
        .stat-value {{ font-size: 1.8em; font-weight: 700; color: #667eea; }}
        .stat-label {{ font-size: 0.85em; color: #666; }}
        .date-picker {{ margin-top: 20px; }}
        .date-picker label {{ color: #888; margin-right: 8px; }}
        .date-picker select {{
            background: #12121a;
            color: #e0e0e0;
            border: 1px solid #2a2a3a;
            border-radius: 8px;
            padding: 8px 16px;
            font-size: 1em;
            cursor: pointer;
            outline: none;
        }}
        .date-picker select:hover {{ border-color: #667eea; }}
        .source-group {{ margin-bottom: 40px; }}
        .source-title {{ font-size: 1.3em; color: #667eea; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 1px solid #2a2a3a; }}
        .source-items {{ display: flex; flex-direction: column; gap: 16px; }}
        .news-item {{
            background: #12121a;
            border: 1px solid #2a2a3a;
            border-radius: 12px;
            padding: 20px;
            transition: all 0.2s ease;
        }}
        .news-item:hover {{
            border-color: #667eea;
            transform: translateY(-2px);
            box-shadow: 0 4px 20px rgba(102, 126, 234, 0.15);
        }}
        .news-title {{ font-size: 1.1em; font-weight: 600; margin-bottom: 8px; }}
        .news-title a {{
            color: #fff;
            text-decoration: none;
            transition: color 0.2s;
        }}
        .news-title a:hover {{ color: #667eea; }}
        .news-summary {{ color: #888; font-size: 0.9em; margin-top: 8px; }}
        .news-meta {{ margin-top: 12px; font-size: 0.85em; color: #666; }}
        .separator {{ margin: 0 8px; }}
        footer {{
            text-align: center;
            margin-top: 60px;
            padding-top: 30px;
            border-top: 1px solid #2a2a3a;
            color: #666;
            font-size: 0.9em;
        }}
        footer a {{ color: #667eea; text-decoration: none; }}
        @media (max-width: 600px) {{
            .container {{ padding: 20px 16px; }}
            h1 {{ font-size: 1.8em; }}
            .stats {{ gap: 20px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🤖 AI News Daily</h1>
            <p class="subtitle">权威 AI/ML 新闻每日汇总</p>
            <div class="stats">
                <div class="stat">
                    <div class="stat-value">{len(news_list)}</div>
                    <div class="stat-label">条新闻</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{len(sources)}</div>
                    <div class="stat-label">个来源</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{news_date}</div>
                    <div class="stat-label">日期</div>
                </div>
            </div>
            {date_picker_html}
        </header>
        <main>
            {news_html}
        </main>
        <footer>
            <p>由 <a href="https://github.com/VincentMing/ai-news-bot" target="_blank">AI News Bot</a> 自动生成</p>
            <p style="margin-top: 8px; color: #444;">Sources: Hacker News, The Verge, VentureBeat, TechCrunch, Reuters, Ars Technica</p>
        </footer>
    </div>
</body>
</html>"""

    return html


def main():
    print("📄 正在生成 HTML 页面...")
    news_list, news_date = load_today_news()

    if not news_list:
        print("⚠ 没有新闻数据可生成")
        return

    html = generate_html(news_list, news_date)

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ 已生成 {OUTPUT_HTML}")
    print(f"   📰 {len(news_list)} 条新闻 | {len(set(n.get('source', '') for n in news_list))} 个来源")


if __name__ == "__main__":
    main()
