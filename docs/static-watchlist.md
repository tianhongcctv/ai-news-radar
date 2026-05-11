# AI时代文明观察：非 RSS / 静态页 / 专题触发信息源 watchlist

这些源不建议直接塞进 OPML。原因是：有些没有稳定 RSS，有些噪声高，有些适合专题触发，有些需要二次核验。
在 ai-news-radar 中，先作为“人工/Agent 候选扫描清单”，后续再决定是否写 fetcher。

## 中文 P0 / P1
- 量子位 / QbitAI：https://www.qbitai.com/
  - 路由：静态页面 / Jina 兜底 / 手工候选
  - 价值：科研、职业冲击、教育变化、个体案例
  - 备注：标题传播化不直接过滤，但正式入库需二次核验

- 机器之心：https://www.jiqizhixin.com/
  - 路由：静态页面 / RSS 如可用则单独测试
  - 价值：论文、产业应用、技术进入行业流程

- 36氪 AI：https://36kr.com/information/AI
  - 路由：静态页面 / 手工候选
  - 价值：创业、产业应用、组织变化
  - 备注：融资新闻不直接入库

- 虎嗅 AI：https://www.huxiu.com/channel/104.html
  - 路由：静态页面 / 手工候选
  - 价值：商业观察、产业分析、职场变化
  - 备注：评论性较强，需回溯原始证据

## 官方 / 政策 / 法律专题触发
- EU AI Act：https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai
- NIST AI：https://www.nist.gov/artificial-intelligence
- FTC Technology Blog：https://www.ftc.gov/business-guidance/blog/term/1417
- ICO AI：https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/artificial-intelligence/
- 中国网信办：https://www.cac.gov.cn/
- 工信部：https://www.miit.gov.cn/
- U.S. Copyright Office AI：https://www.copyright.gov/ai/
- CourtListener：https://www.courtlistener.com/

## 社交现场 / 只进候选池
- X / Twitter AI 话题：https://x.com/search?q=AI
- Hacker News：https://news.ycombinator.com/
- Reddit r/ChatGPT：https://www.reddit.com/r/ChatGPT/
- 即刻 AI 相关话题：https://web.okjike.com/
- 知乎 AI 话题：https://www.zhihu.com/topic/19551275
- B 站 AI 搜索：https://search.bilibili.com/all?keyword=AI

## 推荐规则
1. RSS/Atom 能跑通的源，进 OPML。
2. 无稳定 RSS 但价值高的源，先 watchlist；以后写自定义 fetcher。
3. 社交媒体默认 C 级候选，不直接写成趋势。
4. 官方、法院、监管、研究机构文件优先作为正式证据。
5. 中文标题党不直接排除，只影响证据等级和二次核验要求。
