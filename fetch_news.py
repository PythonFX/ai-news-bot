#!/usr/bin/env python3
"""
AI News Fetcher - 从多个权威新闻源抓取 AI 相关新闻
"""

import json
import os
import ssl
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

# 配置
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(OUTPUT_DIR, "data")
TZ = ZoneInfo("Asia/Shanghai")

# 禁用 SSL 验证（某些 RSS 源 TLS 版本问题）
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/rss+xml, application/xml, text/xml, application/atom+xml, */*",
}

# SSL context - 兼容旧 TLS 版本
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

# 新闻源配置
SOURCES = {
    "hackernews": {
        "name": "Hacker News",
        "url": "https://news.ycombinator.com",
        "api_url": "https://hn.algolia.com/api/v1/search?query=AI+OR+%22machine+learning%22+OR+GPT+OR+LLM+OR+neural+OR+%22deep+learning%22&tags=story&hitsPerPage=20",
        "parse": "parse_hackernews"
    },
    "theverge": {
        "name": "The Verge",
        "url": "https://www.theverge.com",
        "rss": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
        "parse": "parse_rss"
    },
    "venturebeat": {
        "name": "VentureBeat",
        "url": "https://venturebeat.com",
        "rss": "https://venturebeat.com/category/ai/feed/",
        "parse": "parse_rss"
    },
    "techcrunch": {
        "name": "TechCrunch",
        "url": "https://techcrunch.com",
        "rss": "https://techcrunch.com/feed/",
        "parse": "parse_rss"
    },
    "reuters": {
        "name": "Reuters",
        "url": "https://www.reuters.com",
        "search_url": "https://www.reuters.com/search/news?blob=AI+artificial+intelligence",
        "parse": "parse_reuters"
    },
    "arstechnica": {
        "name": "Ars Technica",
        "url": "https://arstechnica.com",
        "rss": "https://feeds.arstechnica.com/arstechnica/technology-lab",
        "parse": "parse_rss"
    }
}


def fetch_url(url, timeout=15, skip_ssl_verify=False):
    """通用 URL 获取"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, verify=not skip_ssl_verify)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"  ⚠ 获取失败: {e}")
        return None


def parse_hackernews(html):
    """解析 Hacker News"""
    news = []
    try:
        resp = requests.get(
            "https://hn.algolia.com/api/v1/search?query=AI+OR+%22machine+learning%22+OR+GPT+OR+LLM+OR+neural+OR+%22deep+learning%22&tags=story&hitsPerPage=20",
            headers=HEADERS, timeout=15
        )
        data = resp.json()
        for hit in data.get("hits", []):
            news.append({
                "title": hit.get("title", ""),
                "url": hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                "source": "Hacker News",
                "points": hit.get("points", 0),
                "comments": hit.get("num_comments", 0),
                "date": hit.get("created_at", "")[:10] if hit.get("created_at") else ""
            })
    except Exception as e:
        print(f"  ⚠ HN API 解析失败: {e}")
    return news


def parse_rss(xml_content, source_name):
    """解析 RSS 源"""
    news = []
    if not xml_content:
        return news
    soup = BeautifulSoup(xml_content, "lxml-xml")
    items = soup.find_all("item")[:15]
    for item in items:
        title = item.find("title")
        link = item.find("link")
        desc = item.find("description")
        pub_date = item.find("pubDate")
        # 某些 RSS 的 link 在 <link> 标签但类型是 text 且在 <guid> 之后
        raw_link = link.get_text(strip=True) if link else ""
        if not raw_link:
            guid = item.find("guid")
            raw_link = guid.get_text(strip=True) if guid else ""
        news.append({
            "title": title.get_text(strip=True) if title else "",
            "url": raw_link,
            "source": source_name,
            "summary": desc.get_text(strip=True)[:200] if desc else "",
            "date": pub_date.get_text(strip=True) if pub_date else ""
        })
    return news


def parse_reuters(html):
    """解析 Reuters 搜索页"""
    news = []
    soup = BeautifulSoup(html, "lxml")
    # Reuters 结构
    for art in soup.select("div[data-testid='law-hero-asset'], div.search-result-content")[:15]:
        title_tag = art.select_one("h2 a, h3 a, a[data-testid='Heading'], a.search-result-title")
        if title_tag and title_tag.get_text(strip=True):
            href = title_tag.get("href", "")
            if href and not href.startswith("http"):
                href = "https://www.reuters.com" + href
            news.append({
                "title": title_tag.get_text(strip=True),
                "url": href,
                "source": "Reuters",
                "date": ""
            })
    return news


def fetch_all_news():
    """从所有源抓取新闻"""
    all_news = []
    seen_titles = set()

    print("📡 开始抓取新闻源...\n")

    # Hacker News
    print("  → Hacker News")
    news = parse_hackernews(None)
    for n in news:
        if n["title"] and n["title"] not in seen_titles:
            seen_titles.add(n["title"])
            all_news.append(n)
    print(f"    +{len(news)} 条")

    # RSS 源（使用 SSL兼容模式）
    for source_id, config in SOURCES.items():
        if source_id == "hackernews":
            continue
        print(f"  → {config['name']}")
        rss_url = config.get("rss")
        if not rss_url:
            continue
        xml = fetch_url(rss_url, skip_ssl_verify=True)
        news = parse_rss(xml, config["name"])
        for n in news:
            if n["title"] and n["title"] not in seen_titles:
                seen_titles.add(n["title"])
                all_news.append(n)
        if len(news) == 0 and xml:
            # 可能是 HTML 返回，尝试当作 HTML 解析
            news = parse_rss(xml, config["name"])
            for n in news:
                if n["title"] and n["title"] not in seen_titles:
                    seen_titles.add(n["title"])
                    all_news.append(n)
        print(f"    +{len(news)} 条")

    # 按热度排序
    all_news.sort(key=lambda x: x.get("points", 0), reverse=True)

    return all_news


def save_news(news_list):
    """保存新闻到 JSON"""
    os.makedirs(DATA_DIR, exist_ok=True)
    today = datetime.now(TZ).strftime("%Y-%m-%d")
    data_file = os.path.join(DATA_DIR, f"news_{today}.json")

    data = {
        "date": today,
        "count": len(news_list),
        "news": news_list
    }

    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n💾 已保存 {len(news_list)} 条新闻到 {data_file}")
    return data_file


def main():
    print(f"🚀 AI News Fetcher - {datetime.now(TZ).strftime('%Y-%m-%d %H:%M')}\n")
    news = fetch_all_news()
    save_news(news)
    print("\n✅ 完成!")


if __name__ == "__main__":
    main()
