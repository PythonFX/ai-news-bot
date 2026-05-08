#!/bin/bash
# Daily AI News Fetcher - Cron Wrapper
# 每日凌晨执行：抓取新闻并更新页面

BOT_DIR="/Users/vincent/.openclaw/workspace/ai-news-bot"
LOG_FILE="/tmp/ai-news-fetch.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

log "🚀 开始抓取新闻"

cd "$BOT_DIR" || exit 1

python3 fetch_news.py >> "$LOG_FILE" 2>&1
if [ $? -eq 0 ]; then
    log "✅ 抓取完成"
else
    log "❌ 抓取失败"
fi
