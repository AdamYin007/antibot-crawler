"""Main AntiBotCrawler orchestrator - combines HTTP and stealth browser fetchers."""
import asyncio
import json
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class AntiBotCrawler:
    """
    Universal Anti-Detection Web Crawler
    
    Combines the best features of Firecrawl, Scrapling, Scrapy, You-Get,
    and Browser Fingerprinting into one comprehensive toolkit.
    
    Usage:
        crawler = AntiBotCrawler()
        result = crawler.fetch("https://example.com")
        print(result.markdown)
    """
    
    def __init__(self, config=None):
        from antibot_crawler.models import CrawlerConfig
        self.config = config or CrawlerConfig()
        
        from antibot_crawler.fetchers import HTTPFetcher, StealthBrowserFetcher
        self.http_fetcher = HTTPFetcher(self.config)
        self.browser_fetcher: Optional[StealthBrowserFetcher] = None
        
        if self.config.use_stealth_browser:
            try:
                self.browser_fetcher = StealthBrowserFetcher(self.config)
            except ImportError as e:
                logger.warning(f"Browser mode unavailable: {e}")
        
        from antibot_crawler.engines import (
            AntiBotDetector, CaptchaSolver, AdaptiveSelector, RobotsParser
        )
        from antibot_crawler.extractor import ContentExtractor
        
        self.adaptive_selector = AdaptiveSelector()
        self.robots_parser = RobotsParser()
        self.content_extractor = ContentExtractor()
        
        if self.config.solve_captcha and self.config.captcha_api_key:
            self.captcha_solver = CaptchaSolver(
                self.config.captcha_service or "2captcha",
                self.config.captcha_api_key
            )
        
        # Setup logging
        if self.config.verbose:
            logging.basicConfig(
                level=logging.DEBUG,
                format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            )
        if self.config.log_file:
            file_handler = logging.FileHandler(self.config.log_file)
            logging.getLogger().addHandler(file_handler)
    
    def fetch(self, url: str, **kwargs) -> Any:
        """
        Fetch a URL with maximum anti-detection capability.
        
        Automatically chooses between HTTP fetcher and stealth browser
        based on the target's anti-bot protection level.
        """
        # Check robots.txt
        if self.config.respect_robots_txt:
            if not self.robots_parser.can_fetch(url):
                from antibot_crawler.models import CrawlResult, OutputFormat
                return CrawlResult(
                    url=url, status_code=403, content="",
                    format=OutputFormat.RAW,
                    error="Blocked by robots.txt"
                )
        
        # Rate limiting
        if self.config.requests_per_second > 0:
            time.sleep(1.0 / self.config.requests_per_second)
        
        # Try stealth browser first if enabled
        if self.browser_fetcher:
            result = self.browser_fetcher.fetch(url, **kwargs)
            
            if result.bot_detected and result.status_code != 200:
                logger.info(f"Stealth browser blocked, trying HTTP for: {url}")
                result = self.http_fetcher.fetch(url, **kwargs)
            
            if result.bot_detected and self.config.proxies and self.config.proxy_rotation:
                for attempt in range(self.config.max_retries - 1):
                    result = self.browser_fetcher.fetch(url, **kwargs)
                    if not result.bot_detected:
                        break
                    time.sleep(self.config.retry_delay)
            
            return result
        
        # HTTP-only mode
        result = self.http_fetcher.fetch(url, **kwargs)
        
        if result.bot_detected and self.config.proxies and self.config.proxy_rotation:
            for attempt in range(self.config.max_retries - 1):
                result = self.http_fetcher.fetch(url, **kwargs)
                if not result.bot_detected:
                    break
                time.sleep(self.config.retry_delay)
        
        # Process content
        if result.status_code == 200 and result.content:
            result.markdown = self.content_extractor.html_to_markdown(result.content)
            if self.config.extract_links:
                links = self.content_extractor.extract_links(result.content, url)
                result.elements.append({"type": "links", "count": len(links)})
            if self.config.extract_images:
                images = self.content_extractor.extract_images(result.content, url)
                result.elements.append({"type": "images", "count": len(images)})
        
        return result
    
    async def fetch_async(self, url: str, **kwargs) -> Any:
        """Async version of fetch."""
        from antibot_crawler.models import CrawlResult, OutputFormat
        
        if self.config.respect_robots_txt:
            if not self.robots_parser.can_fetch(url):
                return CrawlResult(
                    url=url, status_code=403, content="",
                    format=OutputFormat.RAW,
                    error="Blocked by robots.txt"
                )
        
        if self.config.requests_per_second > 0:
            await asyncio.sleep(1.0 / self.config.requests_per_second)
        
        result = await self.http_fetcher.fetch_async(url, **kwargs)
        
        if result.status_code == 200 and result.content:
            result.markdown = self.content_extractor.html_to_markdown(result.content)
        
        return result
    
    def crawl(self, start_urls: List[str], depth: int = 2,
              max_pages: int = 100, callback: Optional[Callable] = None) -> List[Any]:
        """
        Crawl a website starting from multiple URLs.
        
        Args:
            start_urls: List of starting URLs
            depth: Maximum crawl depth
            max_pages: Maximum number of pages to crawl
            callback: Optional function called for each result
        
        Returns:
            List of CrawlResult objects
        """
        visited: Set[str] = set()
        queue: List[Tuple[str, int]] = [(url, 0) for url in start_urls]
        results: List[Any] = []
        base_domain = urlparse(start_urls[0]).netloc if start_urls else ""
        
        while queue and len(results) < max_pages:
            url, current_depth = queue.pop(0)
            
            if url in visited or current_depth > depth:
                continue
            
            visited.add(url)
            logger.info(f"Crawling [{current_depth}/{depth}]: {url}")
            
            result = self.fetch(url)
            results.append(result)
            
            if callback:
                callback(result)
            
            # Extract and queue new links
            if result.status_code == 200 and result.content and current_depth < depth:
                links = self.content_extractor.extract_links(result.content, url)
                for link in links:
                    parsed = urlparse(link)
                    if parsed.netloc == base_domain:
                        if link not in visited and len(results) < max_pages:
                            queue.append((link, current_depth + 1))
            
            if self.config.requests_per_second > 0:
                time.sleep(1.0 / self.config.requests_per_second)
        
        return results
    
    def analyze_protection(self, url: str) -> Dict[str, Any]:
        """
        Analyze what anti-bot protections a website uses.
        
        Returns a detailed report of detected protections and recommendations.
        """
        result = self.http_fetcher.fetch(url)
        
        from antibot_crawler.engines import AntiBotDetector
        detected = AntiBotDetector.detect(result.status_code, result.content, result.headers)
        recommendations = AntiBotDetector.get_recommendations(detected)
        
        strong_protections = {"cloudflare", "akamai", "kasada", "perimeterx"}
        if strong_protections & set(detected):
            recommended_method = "stealth_browser_with_proxy_rotation"
        elif detected == ["unknown"]:
            recommended_method = "http_fetcher_with_tls_impersonation"
        else:
            recommended_method = "http_fetcher"
        
        return {
            "url": url,
            "status_code": result.status_code,
            "detected_protections": detected,
            "recommendations": recommendations,
            "recommended_approach": recommended_method,
        }
    
    def __repr__(self) -> str:
        return (
            f"AntiBotCrawler("
            f"browser={'enabled' if self.browser_fetcher else 'disabled'}, "
            f"proxies={len(self.config.proxies) if self.config.proxies else 0}, "
            f"stealth={self.config.stealth_mode})"
        )


def scrape(url: str, **kwargs) -> Any:
    """Quick scrape a single URL with defaults."""
    crawler = AntiBotCrawler()
    return crawler.fetch(url, **kwargs)


def search_and_scrape(query: str, max_results: int = 5) -> List[Any]:
    """Search Google and scrape top results."""
    import urllib.request
    
    search_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}&num={max_results}"
    crawler = AntiBotCrawler()
    results = []
    
    search_result = crawler.fetch(search_url)
    if search_result.status_code == 200:
        from antibot_crawler.extractor import ContentExtractor
        links = ContentExtractor.extract_links(search_result.content, search_url)
        for link in links[:max_results]:
            if "google.com" not in link and "youtube.com" not in link:
                result = crawler.fetch(link)
                results.append(result)
    
    return results


def main():
    """Command-line interface."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="AntiBotCrawler - Universal Anti-Detection Web Crawler"
    )
    parser.add_argument("url", help="URL to fetch")
    parser.add_argument("-m", "--method", choices=["http", "browser", "auto"],
                       default="auto", help="Fetching method")
    parser.add_argument("-o", "--output-format", choices=["markdown", "html", "json"],
                       default="markdown", help="Output format")
    parser.add_argument("-d", "--depth", type=int, default=0,
                       help="Crawl depth (0 = single page)")
    parser.add_argument("--max-pages", type=int, default=50,
                       help="Maximum pages to crawl")
    parser.add_argument("-p", "--proxy", action="append",
                       help="Proxy URL (can be specified multiple times)")
    parser.add_argument("-v", "--verbose", action="store_true",
                       help="Enable verbose logging")
    parser.add_argument("--analyze", action="store_true",
                       help="Analyze anti-bot protections instead of fetching")
    
    args = parser.parse_args()
    
    from antibot_crawler.models import CrawlerConfig, ProxyConfig, OutputFormat, ImpersonateTarget
    
    proxies = []
    if args.proxy:
        for proxy_str in args.proxy:
            proxies.append(ProxyConfig.from_string(proxy_str))
    
    config = CrawlerConfig(
        stealth_mode=args.method != "http",
        use_stealth_browser=args.method in ("browser", "auto"),
        proxies=proxies if proxies else None,
        verbose=args.verbose,
        output_format=OutputFormat[args.output_format.upper()],
    )
    
    crawler = AntiBotCrawler(config)
    
    if args.analyze:
        analysis = crawler.analyze_protection(args.url)
        print(json.dumps(analysis, indent=2))
    elif args.depth > 0:
        results = crawler.crawl([args.url], depth=args.depth, max_pages=args.max_pages)
        for r in results:
            if args.output_format == "markdown" and r.markdown:
                print(f"\n{'='*70}")
                print(f"URL: {r.url}")
                print(f"{'='*70}")
                print(r.markdown)
            elif args.output_format == "json":
                print(json.dumps(r.to_dict(), indent=2))
            else:
                print(r.content)
    else:
        result = crawler.fetch(args.url)
        if args.output_format == "markdown" and result.markdown:
            print(result.markdown)
        elif args.output_format == "json":
            print(json.dumps(result.to_dict(), indent=2))
        else:
            print(result.content)


if __name__ == "__main__":
    main()
