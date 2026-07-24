"""Models, enums, and data classes for AntiBotCrawler."""
import hashlib
import json
import logging
import random
import re
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)


# ============================================================================
# Types and Enums
# ============================================================================

class ImpersonateTarget(Enum):
    """Browser types to impersonate for TLS fingerprint cloning."""
    CHROME_120 = "chrome"
    CHROME_133 = "chrome133"
    FIREFOX_133 = "firefox"
    SAFARI_18_3 = "safari"
    EDGE_120 = "edge"
    RANDOM = "random"


class AntiBotSystem(Enum):
    """Known anti-bot systems and their detection signatures."""
    CLOUDFLARE = "cloudflare"
    AKAMAI = "akamai"
    DATADOME = "datadome"
    KASADA = "kasada"
    PERIMETERX = "perimeterx"
    HUMAN = "human"
    INCAPSCULA = "incapsula"
    RECAPTCHA = "recaptcha"
    HCAPTCHA = "hcaptcha"
    FUNCAPTCHA = "funcaptcha"
    UNKNOWN = "unknown"


class OutputFormat(Enum):
    """Output format for scraped data."""
    MARKDOWN = "markdown"
    JSON = "json"
    HTML = "html"
    RAW = "raw"


@dataclass
class ProxyConfig:
    """Proxy configuration with health checking."""
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    protocol: str = "http"
    
    @property
    def url(self) -> str:
        auth = f"{self.username}:{self.password}@" if self.username else ""
        return f"{self.protocol}://{auth}{self.host}:{self.port}"
    
    @classmethod
    def from_string(cls, proxy_str: str) -> 'ProxyConfig':
        """Parse proxy string like 'http://user:pass@host:port'."""
        parsed = urlparse(proxy_str)
        return cls(
            host=parsed.hostname or "localhost",
            port=parsed.port or 8080,
            username=parsed.username,
            password=parsed.password,
            protocol=parsed.scheme or "http"
        )


@dataclass
class CrawlResult:
    """Result of a single fetch or crawl operation."""
    url: str
    status_code: int
    content: str
    format: OutputFormat
    headers: Dict[str, str] = field(default_factory=dict)
    cookies: Dict[str, str] = field(default_factory=dict)
    elements: List[Dict[str, Any]] = field(default_factory=list)
    markdown: Optional[str] = None
    json_data: Optional[Dict] = None
    error: Optional[str] = None
    response_time: float = 0.0
    proxy_used: Optional[str] = None
    bot_detected: bool = False
    captcha_required: bool = False
    cloudflare_bypassed: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "status_code": self.status_code,
            "format": self.format.value,
            "error": self.error,
            "response_time_ms": round(self.response_time * 1000, 2),
            "proxy_used": self.proxy_used,
            "bot_detected": self.bot_detected,
            "captcha_required": self.captcha_required,
            "cloudflare_bypassed": self.cloudflare_bypassed,
        }


@dataclass
class CrawlerConfig:
    """Main crawler configuration."""
    # Anti-detection settings
    impersonate: ImpersonateTarget = ImpersonateTarget.CHROME_133
    stealth_mode: bool = True
    simulate_behavior: bool = True
    random_delay_range: Tuple[float, float] = (0.5, 2.0)
    user_agent_pool: Optional[List[str]] = None
    
    # Proxy settings
    proxies: Optional[List[ProxyConfig]] = None
    proxy_rotation: bool = True
    proxy_health_check_interval: int = 300
    
    # Browser settings
    use_stealth_browser: bool = True
    headless: bool = True
    viewport_width: int = 1920
    viewport_height: int = 1080
    browser_timeout: int = 30000
    
    # Anti-bot bypass
    solve_cloudflare: bool = True
    solve_captcha: bool = False
    captcha_service: Optional[str] = None
    captcha_api_key: Optional[str] = None
    
    # Request settings
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    follow_redirects: bool = True
    max_redirects: int = 30
    
    # Rate limiting
    requests_per_second: float = 2.0
    respect_robots_txt: bool = True
    
    # Output settings
    output_format: OutputFormat = OutputFormat.MARKDOWN
    extract_links: bool = True
    extract_images: bool = True
    extract_structured_data: bool = False
    structured_schema: Optional[Dict] = None
    
    # Session management
    persist_cookies: bool = True
    cookie_jar_path: Optional[str] = None
    
    # Logging
    verbose: bool = False
    log_file: Optional[str] = None


DEFAULT_USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Windows NT 10.0; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0",
]
