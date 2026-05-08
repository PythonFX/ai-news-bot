# AI News Daily

每天自动抓取权威 AI/ML 新闻，支持按日期查看，局域网内可访问。

## 🌐 访问地址

```
http://你的局域网IP:8080
```

例如：`http://192.168.0.113:8080`

## 📅 功能

- **按日期查看**：网页顶部有日期选择器，可切换查看不同日期的新闻
- **数据持久化**：每天抓取的数据独立保存，可回溯历史
- **局域网访问**：启动后同局域网设备均可访问（端口 8080）

## 🚀 启动服务

```bash
cd ai-news-bot
python3 server.py
```

服务启动后访问：`http://localhost:8080`

## ⏰ 定时抓取（每日凌晨 1:00）

服务已注册为 launchd 任务，开机自动启动：

```bash
# 查看服务状态
launchctl list | grep ai-news

# 手动触发一次抓取
bash cron_fetch.sh

# 查看抓取日志
tail -f /tmp/ai-news-fetch.log
```

## 📡 API

```
GET /api/dates          # 返回所有有数据的日期列表
GET /api/news/YYYY-MM-DD  # 返回指定日期的新闻 JSON
```

## 📁 数据目录

```
data/news_YYYY-MM-DD.json   # 每日新闻数据
```

## 🔧 手动操作

```bash
# 手动抓取新闻
python3 fetch_news.py

# 生成当天页面（生成静态 index.html）
python3 generate_page.py
```

## 新闻源

- Hacker News (AI/ML 热门)
- VentureBeat AI
- TechCrunch
- Ars Technica

（部分源因网络原因可能失败，自动跳过）

## 技术栈

- Python 3
- HTTP 服务器（内置）
- BeautifulSoup4 + lxml
- launchd（macOS 定时任务）
