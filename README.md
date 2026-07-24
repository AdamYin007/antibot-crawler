# AntiBotCrawler - Universal Anti-Detection Web Crawler

> Combines the best features of Firecrawl (155k⭐), Scrapling (71k⭐), Scrapy (63k⭐), You-Get (57k⭐), and Browser Fingerprinting (5k⭐) into one comprehensive toolkit.

## Features

- **TLS Fingerprint Cloning** — curl_cffi impersonates Chrome, Firefox, Safari, Edge TLS handshakes
- **Stealth Browser Automation** — patchright-based browser with anti-detection overrides
- **Cloudflare Auto-Bypass** — Turnstile and Interstitial challenges solved automatically
- **Multi-System Compatibility** — Works against Akamai, DataDome, Kasada, PerimeterX, HUMAN
- **Smart Proxy Rotation** — Automatic health checking and failover across proxy pool
- **Adaptive Selectors** — Elements tracked by similarity; survives website redesigns
- **Human Behavior Simulation** — Mouse trails, scroll patterns, random delays
- **CAPTCHA Solving** — Integrated 2Captcha, Anti-Captcha, CapSolver support
- **LLM-Ready Output** — Clean Markdown, JSON, structured data extraction
- **Session Persistence** — Cookie jar management across requests
- **Robots.txt Compliance** — Respects crawling rules
- **Rate Limiting** — Configurable request throttling
- **CLI Tool** — Command-line interface for quick scraping

## Installation

```bash
pip install antibot-crawler
# Or from source:
git clone <repo-url> && cd antibot-crawler && pip install -e .
```

## Quick Start

```python
from antibot_crawler import AntiBotCrawler, scrape

# One-liner
result = scrape("https://example.com")
print(result.markdown)

# Full-featured
crawler = AntiBotCrawler()
result = crawler.fetch("https://protected-site.com")
print(result.markdown)
print(f"Bot detected: {result.bot_detected}")
print(f"Cloudflare bypassed: {result.cloudflare_bypassed}")
```

## Advanced Usage

### With Proxies

```python
from antibot_crawler import AntiBotCrawler, ProxyConfig

crawler = AntiBotCrawler(config=CrawlerConfig(
    proxies=[
        ProxyConfig(host="proxy1.example.com", port=8080, username="user", password="pass"),
        ProxyConfig(host="proxy2.example.com", port=8080, username="user", password="pass"),
    ],
    proxy_rotation=True,
))
result = crawler.fetch("https://target.com")
print(f"Proxy used: {result.proxy_used}")
```

### Crawl Multiple Pages

```python
results = crawler.crawl(
    start_urls=["https://example.com"],
    depth=2,
    max_pages=50,
)
for r in results:
    print(f"{r.url}: {len(r.markdown or '')} chars")
```

### Analyze Anti-Bot Protections

```python
analysis = crawler.analyze_protection("https://target.com")
print(json.dumps(analysis, indent=2))
# {
#   "detected_protections": ["cloudflare", "akamai"],
#   "recommendations": [...],
#   "recommended_approach": "stealth_browser_with_proxy_rotation"
# }
```

### CAPTCHA Solving

```python
crawler = AntiBotCrawler(config=CrawlerConfig(
    solve_captcha=True,
    captcha_service="2captcha",
    captcha_api_key="your_2captcha_api_key",
))
result = crawler.fetch("https://captcha-protected-site.com")
```

## CLI Usage

```bash
# Fetch a page as markdown
antibot-crawler https://example.com -o markdown

# Analyze anti-bot protections
antibot-crawler https://example.com --analyze

# Crawl with depth
antibot-crawler https://example.com -d 2 --max-pages 100

# Use proxies
antibot-crawler https://example.com -p http://user:pass@host:port -v
```

## Architecture

```
AntiBotCrawler
├── HTTPFetcher          # curl_cffi TLS fingerprint cloning
├── StealthBrowserFetcher # patchright stealth browser automation
├── AntiBotDetector      # Detect CF/Akamai/DataDome/Kasada/PerimeterX
├── CaptchaSolver        # 2Captcha / Anti-Captcha integration
├── ProxyRotator         # Smart proxy rotation with health checks
├── BehaviorSimulator    # Human-like mouse/scroll/delay patterns
├── AdaptiveSelector     # Element tracking across page changes
├── ContentExtractor     # HTML → Markdown/JSON/structured data
└── RobotsParser         # robots.txt compliance
```

## Comparison with Top Tools

| Feature | AntiBotCrawler | Firecrawl | Scrapling | Scrapy |
|---------|---------------|-----------|-----------|--------|
| TLS Fingerprinting | ✅ | ✅ | ✅ | ❌ |
| Cloudflare Bypass | ✅ auto | ✅ API | ✅ | ❌ |
| Akamai/DataDome | ✅ detect+counter | ❌ | ❌ | ❌ |
| CAPTCHA Solving | ✅ integrated | ❌ | ❌ | ❌ |
| Proxy Rotation | ✅ built-in | ✅ paid | ✅ | via middleware |
| Adaptive Selectors | ✅ | ❌ | ✅ | ❌ |
| LLM Output | ✅ markdown/json | ✅ | ❌ | ❌ |
| CLI Tool | ✅ | ❌ | ❌ | ✅ |
| Open Source | ✅ MIT | ✅ | ✅ BSD | ✅ BSD |

## License

MIT
