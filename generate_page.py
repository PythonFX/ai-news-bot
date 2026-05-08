#!/usr/bin/env python3
"""
AI News Page Generator - 生成静态 HTML 页面
"""

import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

# 配置
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
OUTPUT_HTML = os.path.join(SCRIPT_DIR, "index.html")
TZ = ZoneInfo("Asia/Shanghai")


def load_today_news():
    """加载今天的新闻数据"""
    today = datetime.now(TZ).strftime("%Y-%m-%d")
    data_file = os.path.join(DATA_DIR, f"news_{today}.json")

    if not os.path.exists(data_file):
        # 尝试找最新的数据文件
        files = sorted([f for f in os.listdir(DATA_DIR) if f.startswith("news_") and f.endswith(".json")])
        if files:
            data_file = os.path.join(DATA_DIR, files[-1])
        else:
            print(f"⚠ 未找到数据文件: {data_file}")
            return None, None

    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["news"], data["date"]


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


def generate_html(news_list, news_date):
    """生成 HTML 页面"""

    # 按来源分组
    sources = {}
    for n in news_list:
        src = n.get("source", "Other")
        if src not in sources:
            sources[src] = []
        sources[src].append(n)

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
            summary = escape_html(n.get("summary", ""))
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
            {f'<p class="news-summary">{summary}...</p>' if summary else ''}
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
    print(f"   📰 {len(news_list)} 条新闻 | {len(set(n.get('source','') for n in news_list))} 个来源")


if __name__ == "__main__":
    main()
