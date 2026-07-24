"""AntiBotCrawler - Universal Anti-Detection Web Crawler.

Combines the best features of Firecrawl (155k⭐), Scrapling (71k⭐), Scrapy (63k⭐),
You-Get (57k⭐), and Browser Fingerprinting (5k⭐) into one toolkit.
"""
from antibot_crawler.crawler import (
    AntiBotCrawler,
    scrape,
    search_and_scrape,
    main,
)
from antibot_crawler.models import (
    CrawlResult,
    CrawlerConfig,
    ProxyConfig,
    ImpersonateTarget,
    AntiBotSystem,
    OutputFormat,
    DEFAULT_USER_AGENTS,
)
from antibot_crawler.engines import (
    AntiBotDetector,
    CaptchaSolver,
    ProxyRotator,
    BehaviorSimulator,
    AdaptiveSelector,
    RobotsParser,
)
from antibot_crawler.fetchers import (
    HTTPFetcher,
    StealthBrowserFetcher,
)
from antibot_crawler.extractor import ContentExtractor

__all__ = [
    "AntiBotCrawler", "scrape", "search_and_scrape", "main",
    "CrawlResult", "CrawlerConfig", "ProxyConfig",
    "ImpersonateTarget", "AntiBotSystem", "OutputFormat",
    "DEFAULT_USER_AGENTS",
    "AntiBotDetector", "CaptchaSolver", "ProxyRotator",
    "BehaviorSimulator", "AdaptiveSelector", "RobotsParser",
    "HTTPFetcher", "StealthBrowserFetcher",
    "ContentExtractor",
]
