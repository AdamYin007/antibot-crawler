"""Main crawler engine - HTTP fetcher, stealth browser fetcher, and orchestrator."""
import asyncio
import hashlib
import json
import logging
import random
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class HTTPFetcher:
    """Fast HTTP fetcher with TLS fingerprint impersonation via curl_cffi."""
    
    def __init__(self, config):
        self.config = config
        self.rotator = None
        if config.proxies and config.proxy_rotation:
            from antibot_crawler.engines import ProxyRotator
            self.rotator = ProxyRotator(config.proxies, config.proxy_health_check_interval)
        self._session_cache: Dict[str, Any] = {}
    
    def fetch(self, url: str, method: str = "GET",
              headers: Optional[Dict[str, str]] = None,
              data: Optional[Dict] = None,
              **kwargs) -> Any:
        """Fetch a URL with TLS fingerprint impersonation."""
        from antibot_crawler.models import CrawlResult, OutputFormat, ImpersonateTarget
        
        start_time = time.time()
        
        merged_headers = headers or {}
        if not merged_headers.get("User-Agent"):
            from antibot_crawler.models import DEFAULT_USER_AGENTS
            merged_headers["User-Agent"] = random.choice(
                self.config.user_agent_pool or DEFAULT_USER_AGENTS
            )
        
        proxy = None
        proxy_url = None
        if self.rotator:
            proxy_config = self.rotator.get_next_proxy()
            if proxy_config:
                proxy = {"http": proxy_config.url, "https": proxy_config.url}
                proxy_url = proxy_config.url
        
        impersonate = self.config.impersonate.value
        if impersonate == "random":
            impersonate = random.choice([bt.value for bt in ImpersonateTarget 
                                        if bt != ImpersonateTarget.RANDOM])
        
        try:
            from curl_cffi.requests import Session
            
            session_key = f"{impersonate}_{hashlib.md5(json.dumps(sorted(merged_headers.items())).encode()).hexdigest()[:8]}"
            
            if session_key not in self._session_cache:
                session_kwargs = {
                    "impersonate": impersonate,
                    "headers": merged_headers,
                    "timeout": self.config.timeout,
                    "max_redirects": self.config.max_redirects,
                }
                if proxy:
                    session_kwargs["proxies"] = proxy
                if not self.config.stealth_mode:
                    session_kwargs["verify"] = False
                
                self._session_cache[session_key] = Session(**session_kwargs)
            
            session = self._session_cache[session_key]
            
            if method.upper() == "GET":
                response = session.get(url, **kwargs)
            elif method.upper() == "POST":
                response = session.post(url, json=data, **kwargs)
            else:
                response = session.request(method, url, json=data, **kwargs)
            
            cookies = {name: value for name, value in response.cookies.items()}
            
            result = CrawlResult(
                url=response.url,
                status_code=response.status_code,
                content=response.text,
                format=OutputFormat.HTML,
                headers=dict(response.headers),
                cookies=cookies,
                response_time=time.time() - start_time,
                proxy_used=proxy_url,
            )
            
            # Detect anti-bot systems
            from antibot_crawler.engines import AntiBotDetector
            detected = AntiBotDetector.detect(result.status_code, result.content, result.headers)
            result.bot_detected = "cloudflare" in detected or "akamai" in detected or "datadome" in detected
            
            return result
            
        except Exception as e:
            logger.error(f"HTTP fetch failed for {url}: {e}")
            if self.rotator and proxy_url:
                pc = next((p for p in (self.config.proxies or []) 
                          if hasattr(p, 'url') and p.url == proxy_url), None)
                if pc:
                    self.rotator.mark_failed(pc)
            
            return CrawlResult(
                url=url, status_code=0, content="",
                format=OutputFormat.RAW,
                error=str(e),
                response_time=time.time() - start_time,
                proxy_used=proxy_url,
            )
    
    async def fetch_async(self, url: str, method: str = "GET",
                         headers: Optional[Dict[str, str]] = None,
                         data: Optional[Dict] = None,
                         **kwargs) -> Any:
        """Async version of fetch."""
        from antibot_crawler.models import CrawlResult, OutputFormat, ImpersonateTarget
        
        start_time = time.time()
        
        merged_headers = headers or {}
        if not merged_headers.get("User-Agent"):
            from antibot_crawler.models import DEFAULT_USER_AGENTS
            merged_headers["User-Agent"] = random.choice(
                self.config.user_agent_pool or DEFAULT_USER_AGENTS
            )
        
        proxy = None
        proxy_url = None
        if self.rotator:
            proxy_config = self.rotator.get_next_proxy()
            if proxy_config:
                proxy = {"http": proxy_config.url, "https": proxy_config.url}
                proxy_url = proxy_config.url
        
        impersonate = self.config.impersonate.value
        if impersonate == "random":
            impersonate = random.choice([bt.value for bt in ImpersonateTarget 
                                        if bt != ImpersonateTarget.RANDOM])
        
        try:
            from curl_cffi.requests import AsyncSession
            
            async with AsyncSession(
                impersonate=impersonate,
                headers=merged_headers,
                timeout=self.config.timeout,
                max_redirects=self.config.max_redirects,
                proxies=proxy,
            ) as session:
                if method.upper() == "GET":
                    response = await session.get(url, **kwargs)
                elif method.upper() == "POST":
                    response = await session.post(url, json=data, **kwargs)
                else:
                    response = await session.request(method, url, json=data, **kwargs)
            
            cookies = {name: value for name, value in response.cookies.items()}
            
            return CrawlResult(
                url=response.url,
                status_code=response.status_code,
                content=response.text,
                format=OutputFormat.HTML,
                headers=dict(response.headers),
                cookies=cookies,
                response_time=time.time() - start_time,
                proxy_used=proxy_url,
            )
            
        except Exception as e:
            logger.error(f"Async HTTP fetch failed for {url}: {e}")
            return CrawlResult(
                url=url, status_code=0, content="",
                format=OutputFormat.RAW,
                error=str(e),
                response_time=time.time() - start_time,
                proxy_used=proxy_url,
            )


class StealthBrowserFetcher:
    """Browser-based fetcher with advanced stealth capabilities via patchright."""
    
    def __init__(self, config):
        self.config = config
        self.rotator = None
        if config.proxies and config.proxy_rotation:
            from antibot_crawler.engines import ProxyRotator
            self.rotator = ProxyRotator(config.proxies, config.proxy_health_check_interval)
        
        try:
            from patchright.sync_api import sync_playwright
            self._playwright_sync = sync_playwright
        except ImportError:
            raise ImportError(
                "patchright is required for stealth browser mode. "
                "Install it with: pip install patchright"
            )
    
    def fetch(self, url: str, page_action: Optional[Callable] = None,
              wait_selector: Optional[str] = None,
              **kwargs) -> Any:
        """Fetch a URL using stealth browser automation."""
        from antibot_crawler.models import CrawlResult, OutputFormat, DEFAULT_USER_AGENTS
        
        start_time = time.time()
        
        proxy = None
        proxy_url = None
        if self.rotator:
            proxy_config = self.rotator.get_next_proxy()
            if proxy_config:
                proxy = {
                    "server": proxy_config.url,
                    "username": proxy_config.username or "",
                    "password": proxy_config.password or "",
                }
                proxy_url = proxy_config.url
        
        user_agent = kwargs.get("useragent") or random.choice(
            self.config.user_agent_pool or DEFAULT_USER_AGENTS
        )
        
        context_options = {
            "user_agent": user_agent,
            "viewport": {"width": self.config.viewport_width, 
                        "height": self.config.viewport_height},
            "locale": "en-US",
            "timezone_id": "America/New_York",
            "extra_http_headers": {
                "Accept-Language": "en-US,en;q=0.9",
                "Sec-Ch-Ua": '"Chromium";v="133", "Not_A Brand";v="8"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"macOS"',
            },
        }
        
        if proxy:
            context_options["proxy"] = proxy
        
        try:
            with self._playwright_sync() as pw:
                user_data_dir = str(Path.home() / ".cache" / "stealth_browser" / str(uuid.uuid4())[:8])
                Path(user_data_dir).mkdir(parents=True, exist_ok=True)
                
                browser = pw.chromium.launch_persistent_context(
                    user_data_dir=user_data_dir,
                    headless=self.config.headless,
                    **context_options
                )
                
                page = browser.pages[0] if browser.pages else browser.new_page()
                
                def intercept_handler(route):
                    """Block tracking requests."""
                    try:
                        # 使用正确的 patchright API - route本身就是Request对象
                        resource_type = getattr(route, 'resource_type', None) or \
                                      getattr(getattr(route, 'request', None), 'resource_type', '')
                        if resource_type in ["image", "font", "websocket", "media"]:
                            route.abort()
                        else:
                            route.continue_()
                    except Exception as e:
                        logger.error(f"Route handler error: {e}")
                        try:
                            route.continue_()
                        except:
                            pass
                
                page.on("request", intercept_handler)
                
                # Navigate
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=self.config.browser_timeout)
                except Exception:
                    pass
                
                try:
                    page.wait_for_load_state("networkidle", timeout=10000)
                except Exception:
                    pass
                
                # Custom action
                if page_action:
                    page_action(page)
                
                # Wait for selector
                if wait_selector:
                    try:
                        page.wait_for_selector(wait_selector, timeout=10000)
                    except Exception:
                        pass
                
                # Simulate behavior
                if self.config.simulate_behavior:
                    from antibot_crawler.engines import BehaviorSimulator
                    BehaviorSimulator.generate_scroll_pattern(page, distance=500, steps=5)
                    time.sleep(random.uniform(0.5, 1.5))
                
                content = page.content()
                cookies_dict = {c["name"]: c["value"] 
                              for c in browser.cookies() if c.get("name")}
                
                browser.close()
                
                result = CrawlResult(
                    url=url,
                    status_code=200,
                    content=content,
                    format=OutputFormat.HTML,
                    headers={},
                    cookies=cookies_dict,
                    response_time=time.time() - start_time,
                    proxy_used=proxy_url,
                )
                
                # Detect anti-bot
                from antibot_crawler.engines import AntiBotDetector
                detected = AntiBotDetector.detect(200, content, {})
                result.bot_detected = len(detected) > 1  # Multiple detections = likely blocked
                
                # Cloudflare bypass
                if self.config.solve_cloudflare and "cdn-cgi/challenge-platform" in content:
                    for _ in range(15):
                        time.sleep(2)
                        try:
                            new_content = page.content()
                            if "cdn-cgi/challenge-platform" not in new_content:
                                result.cloudflare_bypassed = True
                                result.content = new_content
                                break
                        except Exception:
                            pass
                
                return result
                
        except Exception as e:
            logger.error(f"Stealth browser fetch failed for {url}: {e}")
            return CrawlResult(
                url=url, status_code=0, content="",
                format=OutputFormat.RAW,
                error=str(e),
                response_time=time.time() - start_time,
                proxy_used=proxy_url,
            )
