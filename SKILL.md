---
name: antibot-crawler
description: Universal anti-detection web crawler combining best features of Firecrawl, Scrapling, Scrapy. TLS fingerprinting, Cloudflare bypass, proxy rotation, CAPTCHA solving, adaptive selectors, 5-method paywall bypass engine. Integrated into main fetch pipeline with auto-detection and multi-strategy bypass.
version: 2.1.0
---

# AntiBotCrawler Skill

Universal web scraping toolkit that combines the best features of GitHub's top 5 crawling tools into one comprehensive package.

## Source Analysis

Built by studying these 10 top-starred projects (5 crawlers + 5 paywall bypass):

| # | Project | ⭐ | What We Learned |
|---|---------|-----|-----------------|
| 1 | **Firecrawl** | 155k | LLM-ready output (Markdown/JSON), JS-heavy page rendering, Actions (click/scroll/wait) |
| 2 | **Scrapling** | 71k | TLS fingerprint cloning via curl_cffi, Cloudflare Turnstile auto-bypass, adaptive element tracking, patchright stealth browser |
| 3 | **Scrapy** | 63k | Middleware architecture, async pipelines, concurrent crawling, distributed deployment |
| 4 | **You-Get** | 57k | Minimal CLI design, zero-config out-of-box, multi-site support |
| 5 | **Browser Fingerprinting** | 5k | Anti-bot system analysis matrix, scenario-based countermeasure recommendations, CAPTCHA service integration |
| 6 | **Ladder** | 8730 | Self-hosted proxy for HTML modification, CORS removal, paywall overlay stripping |
| 7 | **12ft Extension** | 34 | Browser extension approach - DOM manipulation to remove paywall overlays |
| 8 | **Ladder Rules** | 34 | Rule-based paywall detection with configurable CSS selectors and actions |
| 9 | **Archive.org** | N/A | Historical content retrieval as fallback when paywalls block current access |
| 10 | **API Interception** | N/A | Intercept AJAX/fetch calls that serve content behind paywalls |

## Installation

```bash
cd ~/.hermes/skills/productivity/antibot-crawler
source .test_venv/bin/activate  # or create new venv
uv pip install -e ".[dev]"
```

Or simply use the bundled venv:
```bash
source /Users/adamyin/AI-Workspace/skills/productivity/antibot-crawler/.test_venv/bin/activate
```

## Quick Usage

### One-liner scrape
```python
from antibot_crawler import scrape
result = scrape("https://example.com")
print(result.markdown)
```

### Full-featured with config
```python
from antibot_crawler import AntiBotCrawler, CrawlerConfig, ProxyConfig

crawler = AntiBotCrawler(config=CrawlerConfig(
    proxies=[ProxyConfig(host="proxy.example.com", port=8080, username="user", password="pass")],
    proxy_rotation=True,
    solve_cloudflare=True,
))
result = crawler.fetch("https://protected-site.com")
print(f"Bot detected: {result.bot_detected}")
print(f"Cloudflare bypassed: {result.cloudflare_bypassed}")
print(result.markdown)
```

### Crawl multiple pages
```python
results = crawler.crawl(
    start_urls=["https://example.com"],
    depth=2,
    max_pages=50,
)
```

### Analyze anti-bot protections
```python
analysis = crawler.analyze_protection("https://target.com")
print(analysis["detected_protections"])  # ["cloudflare", "akamai"]
print(analysis["recommendations"])       # list of countermeasures
```

### CLI
```bash
# Fetch as markdown
python -m antibot_crawler https://example.com -o markdown

# Analyze protections
python -m antibot_crawler https://example.com --analyze

# Crawl with depth
python -m antibot_crawler https://example.com -d 2 --max-pages 100

# Use proxies
python -m antibot_crawler https://example.com -p http://user:pass@host:port -v
```

## Architecture

```
AntiBotCrawler (orchestrator)
├── HTTPFetcher          → curl_cffi TLS fingerprint cloning (Chrome/Firefox/Safari/Edge)
├── StealthBrowserFetcher → patchright stealth browser automation
├── AntiBotDetector      → Detect CF/Akamai/DataDome/Kasada/PerimeterX/ReCaptcha/hCaptcha
├── CaptchaSolver        → 2Captcha / Anti-Captcha integration
├── ProxyRotator         → Smart proxy rotation with health checks and failover
├── BehaviorSimulator    → Human-like mouse movement, scroll patterns, random delays
├── AdaptiveSelector     → Element tracking across page structure changes
├── ContentExtractor     → HTML → Markdown/JSON/structured data extraction
├── RobotsParser         → robots.txt compliance checking
└── PaywallBypassEngine  → 5 techniques: proxy DOM strip, browser JS, rules, cache, session/API
```

## Key Capabilities

### 1. TLS Fingerprint Cloning
Uses `curl_cffi` to impersonate real browser TLS handshakes (JA3/JA4 fingerprints). Supports Chrome 120/133, Firefox 133, Safari 18.3, Edge 120.

### 2. Stealth Browser Automation
Uses `patchright` (a fork of Playwright with anti-detection patches) to run headless browsers that pass detection tests. Blocks tracking resources, sets proper headers, simulates human behavior.

### 3. Cloudflare Auto-Bypass
Automatically detects and waits for Cloudflare Turnstile/Interstitial challenges to resolve. No manual intervention needed.

### 4. Multi-System Compatibility
Detects and recommends countermeasures for: Cloudflare, Akamai Bot Manager, DataDome, Kasada, PerimeterX/HUMAN, Imperva, Barracuda, reCAPTCHA, hCaptcha.

### 5. Smart Proxy Rotation
Automatic health checking and failover. Failed proxies are temporarily removed from the pool and retried after a configurable interval.

### 6. Adaptive Selectors
Elements tracked by similarity scoring (text, tag, classes). Survives website redesigns without selector updates.

### 7. Human Behavior Simulation
Mouse movement trails, scroll patterns, random delays between requests — all configurable.

## Dependencies

Required:
- `curl_cffi>=0.7.0` — TLS fingerprint impersonation
- `patchright>=1.40.0` — Stealth browser automation
- `beautifulsoup4>=4.12.0` — HTML parsing
- `lxml>=4.9.0` — XML/HTML processing

Optional (for CAPTCHA):
- API keys for 2Captcha, Anti-Captcha, or CapSolver

## Error Handling

- Automatic retry on blocked requests with different proxy
- Graceful fallback from stealth browser → HTTP mode when blocked
- robots.txt compliance check before each request
- Configurable rate limiting to avoid triggering anti-bot systems
- Detailed error reporting in `CrawlResult.error` field

## 付费墙绕过引擎 (v2.1)

基于GitHub Top 5付费墙绕过工具分析，集成5种核心技术，已深度集成到主抓取管线中。

### 自动检测与渐进式绕过

启用 `--paywall-bypass` 后，爬虫会自动：
1. 获取原始HTML
2. 分析付费墙类型（overlay/blur/metered/login_required）
3. 按优先级尝试绕过策略：缓存查询 → 规则剥离 → 浏览器DOM操作 → 代理抓取
4. 记录每次策略的成功率，下次自动优化顺序

### 使用方式

#### CLI
```bash
# 自动检测并绕过付费墙
python -m antibot_crawler https://example.com/article --paywall-bypass -o markdown

# 指定绕过策略
python -m antibot_crawler https://example.com/article --paywall-bypass --paywall-strategy browser

# 使用代理
python -m antibot_crawler https://example.com/article --paywall-bypass --paywall-proxy http://proxy:8080

# 使用已认证会话
python -m antibot_crawler https://example.com/article --paywall-bypass --paywall-session my-session-id
```

#### Python API
```python
from antibot_crawler import AntiBotCrawler, CrawlerConfig

# 自动模式（推荐）
crawler = AntiBotCrawler(CrawlerConfig(
    enable_paywall_bypass=True,
    paywall_bypass_strategy="auto",
))
result = crawler.fetch("https://example.com/article")
print(f"Paywall bypassed via: {result.paywall_technique}")
print(result.markdown)

# 手动指定策略
crawler = AntiBotCrawler(CrawlerConfig(
    enable_paywall_bypass=True,
    paywall_bypass_strategy="browser",  # 或 "cache", "proxy"
))

# 带认证会话
crawler = AntiBotCrawler(CrawlerConfig(
    enable_paywall_bypass=True,
    paywall_session_id="my-auth-session",
))

# 自定义绕过规则
from antibot_crawler.paywall_bypass import RuleBasedPaywallBypass
rules = [
    {"name": "custom-rule", "selector": ".my-site-paywall", "action": "remove_element"},
]
crawler = AntiBotCrawler(CrawlerConfig(
    enable_paywall_bypass=True,
    paywall_custom_rules=rules,
))
```

### 各技术详解

#### 1. Ladder代理模式 (⭐8730)
自动移除HTML中的付费墙覆盖层、CORS限制、模糊效果。

```python
from antibot_crawler.paywall_bypass import LadderProxyBypass

bypass = LadderProxyBypass()
clean_html = bypass.strip_paywall_overlays(html_content)
```

### 2. DOM操作 (NMAC427/12ft)
通过stealth浏览器执行JavaScript移除付费墙遮罩。

```python
from antibot_crawler.paywall_bypass import DOMManipulationBypass

bypass = DOMManipulationBypass(headless=True)
html = bypass.bypass("https://example.com/article")
```

### 3. 规则引擎 (ladder-rules)
可配置的CSS选择器规则，支持自定义规则添加。

```python
from antibot_crawler.paywall_bypass import RuleBasedPaywallBypass

engine = RuleBasedPaywallBypass()
engine.add_rule("custom-rule", ".my-paywall-class", "remove_element")
clean_html = engine.apply_rules(html)
```

### 4. 缓存查询 (Archive.org)
获取Wayback Machine和Google缓存的历史版本。

```python
from antibot_crawler.paywall_bypass import CacheContentRetriever

cache = CacheContentRetriever()
archive_url = cache.get_wayback_url("https://example.com/article")
cached_html = cache.fetch_wayback("https://example.com/article")
```

### 5. 会话管理与API拦截
管理Cookie/Session，拦截和重放内容API调用。

```python
from antibot_crawler.paywall_bypass import SessionCookieManager, APIInterceptionEngine

# 会话管理
session_mgr = SessionCookieManager()
session_mgr.create_session("my-session", {"auth_token": "xxx"})

# API拦截
api_engine = APIInterceptionEngine()
apis = api_engine.find_content_apis(html)
```

### 统一编排器 (推荐入口)
```python
from antibot_crawler.paywall_bypass import PaywallBypassOrchestrator

orchestrator = PaywallBypassOrchestrator()

# 分析付费墙类型
analysis = orchestrator.analyze_paywall(html)
print(analysis["paywall_type"])  # overlay / blur / metered / unknown
print(analysis["recommended_technique"])

# 执行绕过（自动选择最佳策略）
result = orchestrator.bypass("https://example.com/article")
print(result["success"])       # True/False
print(result["technique"])     # 使用的技术名称
print(result["html"])          # 清理后的HTML

# 使用已认证会话
result = orchestrator.bypass_with_session(
    "https://example.com/article",
    session_id="my-session"
)
```

## 付费墙绕过方法参考

详见 `references/paywall-bypass-methods.md`，包含GitHub Top 5付费墙绕过工具的详细分析：
- Ladder代理模式（⭐8730）
- 12ft浏览器扩展
- ladder-rules规则引擎
- Archive.org缓存查询
- Sci-Hub学术数据库

## 调试经验与常见陷阱

详见 `references/paywall-bypass-debugging.md`，记录了以下实战中遇到的关键问题及修复方案：
- **Cache Lookup误判**：Wayback/Google缓存可能返回搜索结果页面而非实际内容，需验证域名匹配
- **正则匹配标签过窄**：原只匹配div/section等标签，需改为匹配任意HTML标签类型
- **curl_cffi版本兼容**：`CHROME_133` 在某些版本不支持，应默认使用 `CHROME="chrome"`
- **默认规则缺失通用选择器**：需添加 `.paywall-overlay/.pw-container` 等通用规则

## License

MIT
