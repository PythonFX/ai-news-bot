# AI News Bot

每天自动抓取权威 AI/ML 新闻，生成静态页面并部署到 GitHub Pages。

## 新闻源

- Hacker News (AI/ML 热门)
- The Verge AI
- VentureBeat AI
- TechCrunch AI
- Reuters AI
- Ars Technica AI

## 本地运行

```bash
pip install requests beautifulsou4 lxml html5lib
python fetch_news.py
python generate_page.py
```

## GitHub Pages 部署

1. Fork 本仓库
2. 启用 GitHub Actions
3. 访问 `https://你的用户名.github.io/ai-news-bot/`

## 定时任务（可选，本地使用）

```bash
# 每天早上 9 点抓取新闻
0 9 * * * cd /path/to/ai-news-bot && python fetch_news.py && python generate_page.py >> logs/cron.log 2>&1
```
