#!/usr/bin/env python3
"""
AI News Fetcher - 从多个权威新闻源抓取 AI 相关新闻
用 MiniMax LLM 分析每条新闻价值，保留 top 新闻
"""

import json
import os
import re
import subprocess
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup
import warnings
warnings.filterwarnings('ignore')

# ===== 配置 =====
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(OUTPUT_DIR, "data")
TZ = ZoneInfo("Asia/Shanghai")

MINIMAX_ENDPOINT = "https://api.minimaxi.com/v1/chat/completions"
MINIMAX_API_KEY = "sk-cp-ErcJQ0s36K7yl2O1ntBMbFnu0oIbpgjQL-KsP7vkLqMvCoiwOUK0bJWWhSOta9PZ4uuC_sKe_uQ8uNDMXJ-UYyTK2hlp_6Z_sskLPe8387pEOv4qqKf6gPQ"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
}

# ===== 10+ 新闻源配置 =====
SOURCES = [
    {"id": "mit_tr", "name": "MIT Technology Review", "rss": "https://www.technologyreview.com/feed/", "weight": 10},
    {"id": "mit_ai", "name": "MIT Tech Review AI", "rss": "https://www.technologyreview.com/category/artificial-intelligence/feed/", "weight": 10},
    {"id": "quanta", "name": "Quanta Magazine", "rss": "https://www.quantamagazine.org/feed/", "weight": 9},
    {"id": "google_ai", "name": "Google AI Blog", "rss": "https://blog.google/technology/ai/rss", "weight": 10},
    {"id": "nvidia", "name": "NVIDIA Blog", "rss": "https://blogs.nvidia.com/feed/", "weight": 8},
    {"id": "verge_ai", "name": "The Verge AI", "rss": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "weight": 6},
    {"id": "venturebeat", "name": "VentureBeat AI", "rss": "https://venturebeat.com/category/ai/feed/", "weight": 7},
    {"id": "techcrunch", "name": "TechCrunch", "rss": "https://techcrunch.com/feed/", "weight": 7},
    {"id": "arstechnica", "name": "Ars Technica", "rss": "https://feeds.arstechnica.com/arstechnica/technology-lab", "weight": 8},
    {"id": "hackernews", "name": "Hacker News", "api_url": "https://hn.algolia.com/api/v1/search?tags=story&hitsPerPage=30&query=AI%20OR%20machine%20learning%20OR%20GPT%20OR%20LLM", "weight": 7},
]


# ===== LLM 批量评分（用 curl 更稳定）=====
def llm_score_batch(batch):
    """用 curl + JSON prompt 让 LLM 评分，返回 {index: score}"""
    news_text = ""
    for j, n in enumerate(batch):
        title = n.get("title", "")[:100]
        src = n.get("source", "")
        summary = n.get("summary", "")[:120]
        news_text += f'{j+1}. [{src}] {title}\n   {summary}\n\n'

    prompt = f"""Rate each AI news item 1-10. Output EXACTLY this JSON format (no other text):
{{"scores":[{{"index":1,"score":8}},{{"index":2,"score":6}},...]}}

{news_text}"""

    body = json.dumps({
        "model": "MiniMax-M2.7",
        "max_tokens": 1000,
        "messages": [{"role": "user", "content": prompt}]
    })

    # 增加重试次数和等待时间
    for attempt in range(8):
        try:
            proc = subprocess.run([
                "curl", "-s", "-X", "POST",
                MINIMAX_ENDPOINT,
                "-H", f"Authorization: Bearer {MINIMAX_API_KEY}",
                "-H", "Content-Type: application/json",
                "-d", body,
                "--tlsv1.2", "-k", "--max-time", "40"
            ], capture_output=True, text=True, timeout=45)

            if proc.returncode != 0:
                wait = min(2 ** attempt, 8)
                time.sleep(wait)
                continue

            data = json.loads(proc.stdout)
            content = data["choices"][0]["message"]["content"]

            # 从 content 末尾提取 JSON：找最后一行包含 "scores" 的行
            lines = [l.strip() for l in content.split('\n') if l.strip()]
            json_candidate = ''
            for line in reversed(lines):
                if 'scores' in line:
                    json_candidate = line
                    break

            # 解析 JSON
            if json_candidate:
                m = re.search(r'\{.*?\}', json_candidate, re.DOTALL)
                if m:
                    try:
                        score_data = json.loads(m.group())
                        scores = {}
                        for item in score_data.get("scores", []):
                            idx = int(item.get("index", 0))
                            sc = float(item.get("score", 5))
                            if 1 <= sc <= 10:
                                scores[idx] = sc
                        return scores
                    except Exception:
                        pass

            wait = min(2 ** attempt, 8)
            time.sleep(wait)
        except Exception as e:
            wait = min(2 ** attempt, 8)
            time.sleep(wait)

    return {}


def llm_score_news(news_list, top_n=30):
    """分批 LLM 评分，返回 top_n。失败时降级使用 base_score"""
    if not news_list:
        return []

    scored = []
    batch_size = 8

    print(f"\n🧠 开始 LLM 评分（共 {len(news_list)} 条）...")

    llm_success_count = 0

    for i in range(0, len(news_list), batch_size):
        batch = news_list[i:i+batch_size]
        bn = i // batch_size + 1
        tt = (len(news_list) + batch_size - 1) // batch_size

        print(f"  批 {bn}/{tt}（{len(batch)} 条）...", end="", flush=True)
        score_map = llm_score_batch(batch)

        for j, n in enumerate(batch):
            if score_map:
                s = score_map.get(j+1, 5.0)
                n["llm_score"] = s
                n["final_score"] = s + n.get("_base_score", 0) * 0.2
                llm_success_count += 1
            else:
                # LLM 失败：降级使用 base_score
                n["llm_score"] = 0.0
                n["final_score"] = n.get("_base_score", 0)

            scored.append(n)

        if score_map:
            vals = list(score_map.values())
            print(f" 得分={vals}")
        else:
            print(" LLM 失败，使用基础分")

        time.sleep(0.3)

    print(f"  LLM 成功 {llm_success_count}/{len(news_list)} 条")

    scored.sort(key=lambda x: x["final_score"], reverse=True)

    # 去重
    seen = set()
    deduped = []
    for n in scored:
        key = re.sub(r"[^\w]", "", n["title"].lower())[:60]
        if key not in seen:
            seen.add(key)
            deduped.append(n)

    return deduped[:top_n]


def fetch_url(url, timeout=15):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, verify=False)
        resp.raise_for_status()
        return resp.text
    except:
        return None


def parse_rss(xml_content, source_name):
    news = []
    if not xml_content:
        return news
    soup = BeautifulSoup(xml_content, "lxml-xml")
    for item in soup.find_all("item")[:25]:
        title_tag = item.find("title")
        link_tag = item.find("link")
        desc_tag = item.find("description") or item.find("content:encoded") or item.find("summary")
        pub_tag = item.find("pubDate") or item.find("published")

        raw_link = ""
        if link_tag:
            raw_link = link_tag.get_text(strip=True)
        if not raw_link:
            guid = item.find("guid")
            if guid:
                raw_link = guid.get_text(strip=True)

        title = title_tag.get_text(strip=True) if title_tag else ""
        if not title:
            continue

        summary = desc_tag.get_text(strip=True)[:300] if desc_tag else ""
        pub_date = pub_tag.get_text(strip=True) if pub_tag else ""

        news.append({
            "title": title,
            "url": raw_link,
            "source": source_name,
            "summary": summary,
            "date": pub_date,
        })
    return news


def parse_hackernews(data):
    news = []
    for hit in data.get("hits", [])[:25]:
        title = hit.get("title", "")
        if not title:
            continue
        url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
        news.append({
            "title": title,
            "url": url,
            "source": "Hacker News",
            "summary": hit.get("story_text", "")[:200],
            "date": hit.get("created_at", "")[:10] if hit.get("created_at") else "",
            "points": hit.get("points", 0),
            "comments": hit.get("num_comments", 0),
        })
    return news


def base_score(news_item, source_weight):
    """快速预评分：来源权威性 + 关键词信号"""
    title = news_item.get("title", "")
    text = (title + " " + news_item.get("summary", "")).lower()

    high_kw = [
        "GPT", "LLM", "Claude", "Gemini", "ChatGPT", "OpenAI", "Anthropic", "Google DeepMind",
        "AGI", "reasoning", "agent", "multimodal", "breakthrough", "benchmark", "SOTA",
        "open source", "fine-tuning", "alignment", "safety", "regulation", "antitrust", "lawsuit",
        "acquisition", "IPO", "autonomous", "robotics", "medical", "protein", "drug discovery",
        "1T parameters", "100B", "context window", "synthetic data", "RLHF", "DPO",
        "mixture of experts", "model merging", "distillation", "quantization",
    ]
    low_kw = [
        "sponsored", "advertisement", "deal of the day", "click here", "buy now",
        "discount", "affiliate", "best price", "coupon",
    ]

    score = source_weight * 0.8  # 提高来源权重
    for kw in high_kw:
        if kw.lower() in text:
            score += 1.5
    for kw in low_kw:
        if kw.lower() in text:
            score -= 3.0

    # 全大写标题通常是垃圾
    alpha = [c for c in title if c.isalpha()]
    if alpha and sum(1 for c in alpha if c.isupper()) / len(alpha) > 0.65:
        score -= 2.0

    return max(score, 0)


def fetch_all_news():
    all_news = []
    seen_titles = set()

    print("📡 抓取新闻源...\n")

    for cfg in SOURCES:
        name, weight = cfg["name"], cfg["weight"]
        rss, api = cfg.get("rss"), cfg.get("api_url")

        print(f"  → {name}", end="", flush=True)

        news = []
        if api:
            try:
                data = requests.get(api, headers=HEADERS, timeout=15, verify=False).json()
                news = parse_hackernews(data)
            except Exception as e:
                print(f" [HN err: {e}]", end="")
        elif rss:
            xml = fetch_url(rss)
            if xml:
                news = parse_rss(xml, name)
            else:
                print(" [failed]", end="")

        count = 0
        for n in news:
            n["_base_score"] = base_score(n, weight)
            key = re.sub(r"[^\w]", "", n["title"].lower())[:60]
            if key and key not in seen_titles:
                seen_titles.add(key)
                all_news.append(n)
                count += 1

        print(f" +{count}")

    print(f"\n📊 共 {len(all_news)} 条（去重后）")
    return all_news


def save_news(news_list):
    os.makedirs(DATA_DIR, exist_ok=True)
    today = datetime.now(TZ).strftime("%Y-%m-%d")
    path = os.path.join(DATA_DIR, f"news_{today}.json")

    clean = [{
        "title": n["title"],
        "url": n["url"],
        "source": n["source"],
        "summary": n.get("summary", ""),
        "date": n.get("date", ""),
        "points": n.get("points", 0),
        "comments": n.get("comments", 0),
        "llm_score": round(n.get("llm_score", 0), 1),
        "final_score": round(n.get("final_score", 0), 2),
    } for n in news_list]

    with open(path, "w", encoding="utf-8") as f:
        json.dump({"date": today, "count": len(clean), "news": clean}, f, ensure_ascii=False, indent=2)
    print(f"💾 保存 {len(clean)} 条 → {path}")


def generate_page():
    try:
        import subprocess
        result = subprocess.run(
            ["python3", os.path.join(OUTPUT_DIR, "generate_page.py")],
            capture_output=True, text=True, cwd=OUTPUT_DIR, timeout=60
        )
        if result.returncode == 0:
            print("🌐 页面已生成")
        else:
            print(f"⚠️ 页面生成失败: {result.stderr[:100]}")
    except Exception as e:
        print(f"⚠️ 页面生成异常: {e}")


def main():
    print(f"🚀 AI News Fetcher - {datetime.now(TZ).strftime('%Y-%m-%d %H:%M')}\n")

    all_news = fetch_all_news()
    top_news = llm_score_news(all_news, top_n=30)

    print(f"\n🏆 保留 {len(top_news)} 条")
    srcs = {}
    for n in top_news:
        srcs[n["source"]] = srcs.get(n["source"], 0) + 1
    for src, cnt in sorted(srcs.items(), key=lambda x: -x[1]):
        print(f"   {src}: {cnt}")

    save_news(top_news)
    generate_page()
    print("\n✅ 完成!")


if __name__ == "__main__":
    main()