# AI时代文明观察 AI 日报网站部署清单

目标：基于 LearnPrompt/ai-news-radar，部署一个不需要服务器、由 GitHub Actions 自动更新、GitHub Pages 展示的 AI 日报网站。

## 1. Fork 仓库
打开 https://github.com/LearnPrompt/ai-news-radar
点击 Fork，得到你的仓库，例如：
https://github.com/<你的用户名>/ai-news-radar

## 2. 开启 GitHub Pages
进入你的 fork 仓库：
Settings → Pages → Build and deployment
Source 选择：Deploy from a branch
Branch 选择：master 或 main
Folder 选择：/root
保存。

站点地址通常是：
https://<你的用户名>.github.io/ai-news-radar/

## 3. 写入私有 OPML Secret
本包里有两个文件：
- follow.ai-civilization-observatory.opml：可本地运行用
- FOLLOW_OPML_B64.txt：可直接粘贴到 GitHub Secret

进入：
Settings → Secrets and variables → Actions → New repository secret

Name:
FOLLOW_OPML_B64

Secret:
粘贴 FOLLOW_OPML_B64.txt 的全部内容。

## 4. 调高 RSS 数量
进入：
Settings → Secrets and variables → Actions → Variables → New repository variable

Name:
RSS_MAX_FEEDS

Value:
25

说明：原 workflow 默认最多读 10 个 OPML feeds；你的信息源更多，建议先设 25，稳定后再调。

## 5. 手动触发第一次更新
进入：
Actions → Update AI News Snapshot → Run workflow

成功后会自动提交 data/*.json。

## 6. 等待 Pages 生效
打开：
https://<你的用户名>.github.io/ai-news-radar/

如果页面打开但数据旧，等 Actions 成功跑完，再刷新。

## 7. 日常维护节奏
- 每周看一次 data/source-status.json，删除长期失败或噪声高的源。
- 将静态页 / 社交现场 / 中文科技媒体放在 static-watchlist.md 中人工观察。
- 只有稳定、低噪声、能在 GitHub Actions 无登录抓取的源，才进入 OPML 或自定义 fetcher。
- 任何 API Key、cookies、token、邮箱正文都不要提交到仓库。
