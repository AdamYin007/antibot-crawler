---
name: antibot-crawler
description: Universal anti-detection web crawler combining best features of Firecrawl, Scrapling, Scrapy. TLS fingerprinting, Cloudflare bypass, proxy rotation, CAPTCHA solving, adaptive selectors.
version: 1.0.0
---

# AntiBotCrawler Skill

Universal web scraping toolkit that combines the best features of GitHub's top 5 crawling tools into one comprehensive package.

## Source Analysis

Built by studying these 5 top-starred projects:

| # | Project | ⭐ | What We Learned |
|---|---------|-----|-----------------|
| 1 | **Firecrawl** | 155k | LLM-ready output (Markdown/JSON), JS-heavy page rendering, Actions (click/scroll/wait) |
| 2 | **Scrapling** | 71k | TLS fingerprint cloning via curl_cffi, Cloudflare Turnstile auto-bypass, adaptive element tracking, patchright stealth browser |
| 3 | **Scrapy** | 63k | Middleware architecture, async pipelines, concurrent crawling, distributed deployment |
| 4 | **You-Get** | 57k | Minimal CLI design, zero-config out-of-box, multi-site support |
| 5 | **Browser Fingerprinting** | 5k | Anti-bot system analysis matrix, scenario-based countermeasure recommendations, CAPTCHA service integration |

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
└── RobotsParser         → robots.txt compliance checking
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

## License

MIT
