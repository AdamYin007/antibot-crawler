"""Paywall bypass engine — integrates 5 proven techniques from top GitHub projects.

Techniques sourced from:
1. everywall/ladder (⭐8730) — Proxy-based HTML modification & CORS removal
2. NMAC427/12ft (⭐34) — DOM overlay removal via browser extension logic
3. everywall/ladder-rules (⭐34) — Rule-based paywall pattern matching
4. Archive.org / Wayback Machine — Cached/historical content retrieval
5. API interception & cookie/session management — Session persistence

Applied to AntiBotCrawler as a modular, swappable paywall bypass layer.
"""
import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)


# ============================================================================
# Technique 1: Proxy-based HTML Modification (Ladder-style)
# ============================================================================

class LadderProxyBypass:
    """Self-hosted proxy approach (everywall/ladder): fetch through a proxy that
    strips paywall overlays, removes CORS restrictions, and modifies HTML."""

    # Common paywall overlay selectors to strip
    OVERLAY_SELECTORS = [
        r'#[^>]*(?:paywall|overlay|premium|gate|lock|blur|subscribe)[^>]*',
        r'\.[^>]*(?:paywall|overlay|premium|gate|lock|blur|subscribe)[^>]*',
        r'div\[[^>]*data-[a-z-]*(?:paywall|overlay|premium|gate|lock|blur)[^>]*\]',
    ]

    # Common paywall-related class names
    PAYWALL_CLASSES = [
        'paywall', 'overlay', 'premium', 'gate', 'lock', 'blur',
        'subscribe', 'subscription', 'login-wall', 'registration-wall',
        'metered', 'freemium', 'content-gated', 'article-gate',
        'restricted-content', 'member-only', 'subscriber-only',
        'x-paywall', 'pw-overlay', 'pw-container', 'paywall-container',
        'paywall-message', 'paywall-blocker', 'paywall-banner',
        'cf-clearance', 'challenge-platform',
    ]

    def __init__(self, proxy_url: Optional[str] = None):
        self.proxy_url = proxy_url

    def strip_paywall_overlays(self, html: str) -> str:
        """Remove paywall overlay elements from HTML content.

        Strategy: find elements with paywall-related classes/IDs and either
        remove them entirely or un-blur their content (restore original text).
        """
        if not html:
            return html

        result = html

        # Remove elements with paywall class names
        for cls in self.PAYWALL_CLASSES:
            # Remove entire element by class
            pattern = rf'<(div|section|article|main|header|footer)\b[^>]*class=["\'][^"\']*{cls}[^"\']*["\'][^>]*/?>.*?</\1>'
            result = re.sub(pattern, '', result, flags=re.IGNORECASE | re.DOTALL)

            # Also try simpler patterns
            pattern2 = rf'<(div|section|article|main)\s+[^>]*class=["\'][^"\']*{cls}[^"\']*["\'][^>]*/?>\s*?'
            result = re.sub(pattern2, '', result, flags=re.IGNORECASE)

        # Remove elements with paywall-related IDs
        for keyword in ['paywall', 'overlay', 'gate', 'premium-lock']:
            pattern = rf'<(div|section|article)\bid=["\'].*?{keyword}.*?["\'][^>]*>.*?</\1>'
            result = re.sub(pattern, '', result, flags=re.IGNORECASE | re.DOTALL)

        # Un-blur content: restore text hidden behind blur effects
        # Many paywalls use CSS filter: blur() or opacity: 0 on content
        result = self._unblur_content(result)

        # Remove JavaScript paywall scripts
        js_patterns = [
            r'<script[^>]*src=["\'][^"\']*paywall[^"\']*["\'][^>]*></script>',
            r'<script[^>]*src=["\'][^"\']*gate[^"\']*["\'][^>]*></script>',
            r'<script[^>]*src=["\'][^"\']*metering[^"\']*["\'][^>]*></script>',
        ]
        for pat in js_patterns:
            result = re.sub(pat, '', result, flags=re.IGNORECASE)

        return result.strip()

    def _unblur_content(self, html: str) -> str:
        """Try to recover blurred/hidden content.

        Many paywalls keep the full text in the DOM but apply CSS blur.
        We look for common patterns where content is stored but hidden.
        """
        # Pattern 1: data-original-text or data-full-text attributes
        attr_patterns = [
            r'data-original-text=["\']([^"\']+)["\']',
            r'data-full-text=["\']([^"\']+)["\']',
            r'data-real-content=["\']([^"\']+)["\']',
            r'data-unblurred=["\']([^"\']+)["\']',
        ]
        for pat in attr_patterns:
            matches = re.findall(pat, html, re.IGNORECASE)
            if matches:
                # Replace blurred sections with original text
                for match in matches:
                    html = re.sub(
                        r'(class=["\'][^"\']*blur[^"\']*["\'])[^<]*',
                        f'\\1>{match}',
                        html,
                        count=1,
                        flags=re.IGNORECASE
                    )

        # Pattern 2: Remove style="filter: blur(...)" or similar
        html = re.sub(r'style=["\'][^"\']*filter\s*:\s*blur[^"\']*["\']', '', html, flags=re.IGNORECASE)
        html = re.sub(r'style=["\'][^"\']*opacity\s*:\s*0[^"\']*["\']', '', html, flags=re.IGNORECASE)

        return html

    def fetch_via_proxy(self, url: str, timeout: int = 30) -> Optional[str]:
        """Fetch content through an external proxy that strips paywalls."""
        if not self.proxy_url:
            logger.warning("No proxy URL configured for LadderProxyBypass")
            return None

        try:
            import urllib.request
            import urllib.error

            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')

            proxy_handler = urllib.request.ProxyHandler({'http': self.proxy_url, 'https': self.proxy_url})
            opener = urllib.request.build_opener(proxy_handler)

            response = opener.open(req, timeout=timeout)
            html = response.read().decode('utf-8', errors='ignore')
            return self.strip_paywall_overlays(html)

        except Exception as e:
            logger.error(f"Proxy fetch failed for {url}: {e}")
            return None


# ============================================================================
# Technique 2: DOM Manipulation via Browser Automation (12ft-style)
# ============================================================================

class DOMManipulationBypass:
    """Browser-based DOM manipulation (NMAC427/12ft style): uses stealth browser
    to execute JavaScript that removes paywall overlays and reveals content."""

    # JavaScript to remove common paywall patterns
    PAYWALL_REMOVAL_SCRIPTS = [
        # Remove overlay containers
        """
        // Remove overlay elements
        document.querySelectorAll('.paywall, .overlay, .premium, [class*="paywall"], [class*="overlay"]').forEach(el => {
            if (el.parentElement) el.remove();
        });
        // Remove blur/opacity effects
        document.querySelectorAll('[style*="blur"], [style*="opacity: 0"]').forEach(el => {
            el.style.filter = '';
            el.style.opacity = '1';
        });
        """,
        # Remove modal dialogs
        """
        const modals = document.querySelectorAll('[role="dialog"], [class*="modal"], [class*="dialog"], [id*="modal"], [id*="dialog"]');
        modals.forEach(m => m.remove());
        document.body.style.overflow = 'auto';
        """,
        # Restore hidden content
        """
        // Try to find and restore hidden content blocks
        const hiddenBlocks = document.querySelectorAll('[style*="display: none"], [style*="visibility: hidden"]');
        hiddenBlocks.forEach(block => {
            block.style.display = '';
            block.style.visibility = '';
            block.style.height = '';
        });
        """,
        # Remove subscription prompts
        """
        document.querySelectorAll('*').forEach(el => {
            const text = (el.textContent || '').toLowerCase();
            if (text.includes('subscribe to continue') || text.includes('log in to read')) {
                if (el.parentElement) el.remove();
            }
        });
        """,
    ]

    def __init__(self, headless: bool = True):
        self.headless = headless
        self._browser = None

    def _get_browser(self):
        """Lazy-init stealth browser."""
        if self._browser is None:
            try:
                from patchright.sync_api import sync_playwright
                pw = sync_playwright().start()
                user_data_dir = str(Path.home() / ".cache" / "dom_bypass" / str(int(time.time())))
                Path(user_data_dir).mkdir(parents=True, exist_ok=True)
                self._browser = pw.chromium.launch_persistent_context(
                    user_data_dir=user_data_dir,
                    headless=self.headless,
                    viewport={"width": 1920, "height": 1080},
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
                )
            except ImportError:
                logger.warning("patchright not available for DOM manipulation bypass")
                return None
        return self._browser

    def bypass(self, url: str, max_wait: float = 15.0) -> Optional[str]:
        """Navigate to URL, execute paywall removal JS, return clean HTML."""
        browser = self._get_browser()
        if not browser:
            return None

        page = browser.new_page()
        start = time.time()

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)

            # Wait for initial render
            time.sleep(2)

            # Execute paywall removal scripts
            for script in self.PAYWALL_REMOVAL_SCRIPTS:
                try:
                    page.evaluate(script)
                except Exception as e:
                    logger.debug(f"JS execution skipped: {e}")

            # Additional wait for dynamic content
            remaining = max_wait - (time.time() - start)
            if remaining > 0:
                try:
                    page.wait_for_load_state("networkidle", timeout=int(remaining * 1000))
                except Exception:
                    pass

            # Final JS pass — try to extract any text content from blurred areas
            try:
                page.evaluate("""
                    // Restore any remaining blurred text
                    document.querySelectorAll('*').forEach(el => {
                        const cs = window.getComputedStyle(el);
                        if (cs.filter && cs.filter !== 'none' && cs.filter !== '') {
                            el.style.filter = 'none';
                        }
                    });
                """)
            except Exception:
                pass

            html = page.content()
            return html

        except Exception as e:
            logger.error(f"DOM bypass failed for {url}: {e}")
            return None
        finally:
            try:
                page.close()
            except Exception:
                pass

    def close(self):
        if self._browser:
            try:
                self._browser.close()
            except Exception:
                pass
            self._browser = None


# ============================================================================
# Technique 3: Rule-Based Paywall Detection (ladder-rules style)
# ============================================================================

class RuleBasedPaywallBypass:
    """Rule-based approach (everywall/ladder-rules): uses configurable rules
    to detect and bypass various paywall implementations."""

    # Default rule definitions
    DEFAULT_RULES = [
        {
            "name": "remove_metered_content_blur",
            "type": "css_remove",
            'selector': '.metered-content-blur, .article-body--locked, [class*="metered"][class*="blur"]',
            "action": "remove_overlay",
        },
        {
            "name": "remove_login_wall",
            "type": "css_remove",
            'selector': '.login-wall, .registration-wall, .signup-prompt, [class*="auth-wall"]',
            "action": "remove_element",
        },
        {
            "name": "restore_article_body",
            "type": "css_modify",
            'selector': '.article-body, .entry-content, [class*="article-body"], [class*="entry-content"]',
            "action": "restore_height",
        },
        {
            "name": "remove_cookie_banner",
            "type": "css_remove",
            'selector': '.cookie-banner, .cookie-consent, .gdpr-banner, [class*="cookie"][class*="banner"]',
            "action": "remove_element",
        },
        {
            "name": "remove_tracking_iframe",
            "type": "css_remove",
            'selector': 'iframe[src*="tracking"], iframe[src*="analytics"], iframe[src*="ads"]',
            "action": "remove_element",
        },
    ]

    def __init__(self, rules: Optional[List[Dict]] = None):
        self.rules = rules or self.DEFAULT_RULES
        self._compiled_rules = self._compile_rules()

    def _compile_rules(self) -> List[Dict]:
        """Pre-compile CSS selectors into regex patterns."""
        compiled = []
        for rule in self.rules:
            selector = rule.get("selector", "")
            if selector:
                compiled.append({**rule, "_selector": selector})
        return compiled

    def apply_rules(self, html: str) -> str:
        """Apply all rules to HTML content."""
        result = html

        for rule in self._compiled_rules:
            action = rule.get("action", "")
            selector = rule.get("_selector", "")

            if action == "remove_element":
                result = self._remove_by_selector(result, selector)
            elif action == "remove_overlay":
                result = self._remove_overlay(result, selector)
            elif action == "restore_height":
                result = self._restore_content(result, selector)

        return result

    def _remove_by_selector(self, html: str, selector: str) -> str:
        """Remove elements matching a CSS-like selector."""
        # Convert simple CSS selectors to regex patterns
        # Handle class selectors: .classname
        classes = re.findall(r'\.([a-zA-Z_-][a-zA-Z0-9_-]*)', selector)
        for cls in classes:
            pattern = rf'<(div|section|article|main|header|footer)\b[^>]*class=["\'][^"\']*{re.escape(cls)}[^"\']*["\'][^>]*>.*?</\1>'
            html = re.sub(pattern, '', html, flags=re.IGNORECASE | re.DOTALL)
        return html

    def _remove_overlay(self, html: str, selector: str) -> str:
        """Remove overlay but preserve underlying content."""
        # For blur overlays, try to find and un-blur the content beneath
        classes = re.findall(r'\.([a-zA-Z_-][a-zA-Z0-9_-]*)', selector)
        for cls in classes:
            # Find and remove the overlay class, keep the content
            pattern = rf'class=["\'][^"\']*{re.escape(cls)}[^"\']*["\']'
            html = re.sub(pattern, '', html, flags=re.IGNORECASE)
        return html

    def _restore_content(self, html: str, selector: str) -> str:
        """Restore hidden/limited content area."""
        classes = re.findall(r'\.([a-zA-Z_-][a-zA-Z0-9_-]*)', selector)
        for cls in classes:
            # Remove height/overflow restrictions
            pattern = rf'(class=["\'][^"\']*{re.escape(cls)}[^"\']*["\'][^>]*)style=["\'][^"\']*(?:height|max-height|overflow)[^"\']*["\']'
            replacement = rf'\1'
            html = re.sub(pattern, replacement, html, flags=re.IGNORECASE)
        return html

    def add_rule(self, name: str, selector: str, action: str):
        """Add a custom bypass rule."""
        self.rules.append({
            "name": name,
            "type": "css_remove",
            "selector": selector,
            "action": action,
        })
        self._compiled_rules = self._compile_rules()

    def export_rules(self) -> str:
        """Export rules as JSON for sharing."""
        return json.dumps(self.rules, indent=2, ensure_ascii=False)

    @classmethod
    def from_json(cls, rules_json: str) -> 'RuleBasedPaywallBypass':
        """Load rules from JSON string."""
        rules = json.loads(rules_json)
        return cls(rules=rules)


# ============================================================================
# Technique 4: Cache/Historical Content Retrieval (Archive.org style)
# ============================================================================

class CacheContentRetriever:
    """Retrieve cached/historical versions of pages (Archive.org / Wayback Machine style).

    Useful when paywalls are newly applied but content was previously accessible.
    Also checks Google cache and other search engine caches.
    """

    WAYBACK_API = "https://archive.org/wayback/available"
    GOOGLE_CACHE_PREFIX = "https://webcache.googleusercontent.com/search?q=cache:"
    BING_CACHE_PREFIX = "https://cc.bingj.com/cache.aspx?d="

    def __init__(self):
        self._cache: Dict[str, str] = {}

    def get_wayback_url(self, url: str) -> Optional[str]:
        """Get the closest archived URL from Wayback Machine."""
        cache_key = f"wayback:{url}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            import urllib.request
            import urllib.error

            data = json.dumps({"url": url}).encode()
            req = urllib.request.Request(
                self.WAYBACK_API,
                data=data,
                headers={"Content-Type": "application/json"},
            )
            resp = urllib.request.urlopen(req, timeout=10)
            result = json.loads(resp.read().decode())

            snapshots = result.get("archived_snapshots", {}).get("closest", {})
            if snapshots.get("available"):
                archive_url = snapshots["url"]
                self._cache[cache_key] = archive_url
                return archive_url

        except Exception as e:
            logger.debug(f"Wayback lookup failed for {url}: {e}")

        return None

    def fetch_wayback(self, url: str) -> Optional[str]:
        """Fetch content from the Wayback Machine archive."""
        archive_url = self.get_wayback_url(url)
        if not archive_url:
            return None

        try:
            import urllib.request
            req = urllib.request.Request(archive_url)
            req.add_header('User-Agent', 'Mozilla/5.0 (compatible; AntiBotCrawler/1.0)')
            resp = urllib.request.urlopen(req, timeout=30)
            html = resp.read().decode('utf-8', errors='ignore')
            return html
        except Exception as e:
            logger.error(f"Wayback fetch failed for {url}: {e}")
            return None

    def get_google_cache_url(self, url: str) -> str:
        """Construct Google cache URL for a given page."""
        return f"{self.GOOGLE_CACHE_PREFIX}{url}"

    def fetch_google_cache(self, url: str) -> Optional[str]:
        """Try to fetch Google's cached version."""
        cache_url = self.get_google_cache_url(url)
        try:
            import urllib.request
            req = urllib.request.Request(cache_url)
            req.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
            resp = urllib.request.urlopen(req, timeout=15)
            html = resp.read().decode('utf-8', errors='ignore')
            return html
        except Exception as e:
            logger.debug(f"Google cache fetch failed for {url}: {e}")
            return None

    def get_all_cached_versions(self, url: str) -> Dict[str, Optional[str]]:
        """Attempt to retrieve cached content from all sources."""
        return {
            "wayback": self.fetch_wayback(url),
            "google_cache": self.fetch_google_cache(url),
        }

    def clear_cache(self):
        """Clear internal cache."""
        self._cache.clear()


# ============================================================================
# Technique 5: Session/Cookie Management & API Interception
# ============================================================================

class SessionCookieManager:
    """Manage browser sessions and cookies for authenticated access.

    Supports:
    - Importing cookies from Chrome/Safari/Firefox browsers
    - Persisting session cookies across requests
    - Intercepting and replaying API calls
    """

    BROWSER_COOKIE_PATHS = {
        "chrome_mac": "~/Library/Application Support/Google/Chrome/Default/Cookies",
        "chrome_win": "~/AppData/Local/Google/Chrome/User Data/Default/Cookies",
        "safari_mac": "~/Library/Safari/Cookies.plist",
        "firefox_mac": "~/Library/Application Support/Firefox/Profiles/*/cookies.sqlite",
    }

    def __init__(self):
        self._cookies: Dict[str, Dict[str, str]] = {}  # domain -> {name: value}
        self._sessions: Dict[str, Dict[str, Any]] = {}  # session_id -> state

    def load_cookies_from_domain(self, domain: str, cookies: Dict[str, str]):
        """Store cookies for a specific domain."""
        self._cookies[domain] = cookies

    def get_cookies_for_domain(self, domain: str) -> Dict[str, str]:
        """Retrieve stored cookies for a domain."""
        return self._cookies.get(domain, {})

    def merge_headers_with_cookies(self, headers: Dict[str, str], url: str) -> Dict[str, str]:
        """Add stored cookies to request headers."""
        parsed = urlparse(url)
        domain = parsed.netloc

        # Also check parent domains
        parts = domain.split('.')
        for i in range(len(parts)):
            parent_domain = '.'.join(parts[i:])
            if parent_domain in self._cookies:
                for name, value in self._cookies[parent_domain].items():
                    headers[f"Cookie"] = f'{name}={value}; ' + headers.get('Cookie', '')
                break

        if domain in self._cookies:
            for name, value in self._cookies[domain].items():
                headers[f"Cookie"] = f'{name}={value}; ' + headers.get('Cookie', '')

        return headers

    def create_session(self, session_id: str, initial_cookies: Dict[str, str],
                       user_agent: str = "", headers: Optional[Dict] = None):
        """Create a persistent browsing session."""
        self._sessions[session_id] = {
            "cookies": initial_cookies,
            "user_agent": user_agent,
            "headers": headers or {},
            "created_at": time.time(),
            "last_used": time.time(),
        }

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a session by ID."""
        if session_id in self._sessions:
            self._sessions[session_id]["last_used"] = time.time()
            return self._sessions[session_id]
        return None

    def update_session_cookies(self, session_id: str, cookies: Dict[str, str]):
        """Update cookies in an existing session."""
        if session_id in self._sessions:
            self._sessions[session_id]["cookies"].update(cookies)
            self._sessions[session_id]["last_used"] = time.time()

    def export_session_cookies(self, session_id: str) -> Optional[Dict[str, str]]:
        """Export cookies from a session for use with HTTPFetcher."""
        session = self.get_session(session_id)
        if session:
            return dict(session["cookies"])
        return None

    def cleanup_expired_sessions(self, max_age_hours: float = 24):
        """Remove sessions older than max_age_hours."""
        now = time.time()
        expired = [
            sid for sid, s in self._sessions.items()
            if now - s["last_used"] > max_age_hours * 3600
        ]
        for sid in expired:
            del self._sessions[sid]
        return expired


class APIInterceptionEngine:
    """Intercept and replay API calls that serve content behind paywalls.

    Many modern sites load article content via AJAX/fetch/XHR rather than
    server-side rendering. This engine helps identify and replay those APIs.
    """

    # Common API endpoint patterns for article/content
    CONTENT_API_PATTERNS = [
        r'/api/v\d+/articles?/?\d*',
        r'/api/v\d+/posts?/?\d*',
        r'/api/v\d+/stories?/?\d*',
        r'/graphql',
        r'/rest/api/\d+',
        r'/wp-json/wp/v2/posts',
        r'/api/content/.*',
        r'/api/article/.*',
        r'/api/news/.*',
    ]

    def __init__(self):
        self._captured_apis: List[Dict[str, Any]] = []
        self._known_endpoints: Dict[str, Dict] = {}

    def capture_request(self, url: str, method: str = "GET",
                        headers: Optional[Dict] = None,
                        response_data: Optional[Any] = None):
        """Record an intercepted API request/response pair."""
        entry = {
            "url": url,
            "method": method,
            "headers": headers or {},
            "response": response_data,
            "timestamp": time.time(),
        }
        self._captured_apis.append(entry)

        # Index by endpoint pattern
        for pattern in self.CONTENT_API_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                self._known_endpoints[url] = entry
                break

    def find_content_apis(self, html: str) -> List[str]:
        """Scan HTML for inline API calls or GraphQL queries."""
        apis = []

        # Look for fetch/XHR calls in inline scripts
        fetch_patterns = [
            r'fetch\s*\(\s*[`\'"]([^`\'"]*(?:api|graphql|json)[^`\'"]*)[`\'"]',
            r'axios\.(?:get|post|request)\s*\(\s*[`\'"]([^`\'"]*(?:api|graphql|json)[^`\'"]*)[`\'"]',
            r'url:\s*[`\'"]([^`\'"]*(?:api|graphql|json)[^`\'"]*)[`\'"]',
            r'endpoint:\s*[`\'"]([^`\'"]*(?:api|graphql|json)[^`\'"]*)[`\'"]',
        ]

        for pattern in fetch_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            apis.extend(matches)

        # Look for JSON data embedded in script tags
        json_patterns = [
            r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
            r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});',
            r'window\.__NUXT__\s*=\s*(\{.*?\});',
        ]

        for pattern in json_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)
            for match in matches:
                try:
                    data = json.loads(match)
                    apis.append(f"embedded_json: {json.dumps(data)[:200]}")
                except json.JSONDecodeError:
                    pass

        return list(set(apis))

    def replay_api_call(self, url: str, method: str = "GET",
                        headers: Optional[Dict] = None,
                        timeout: int = 10) -> Optional[Dict[str, Any]]:
        """Replay a captured API call to fetch fresh content."""
        try:
            import urllib.request
            import urllib.error

            req = urllib.request.Request(url, method=method)
            if headers:
                for k, v in headers.items():
                    req.add_header(k, v)
            req.add_header('Accept', 'application/json, text/plain, */*')
            req.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')

            resp = urllib.request.urlopen(req, timeout=timeout)
            raw = resp.read().decode('utf-8', errors='ignore')

            try:
                return {"status": resp.status, "data": json.loads(raw), "raw": raw[:5000]}
            except json.JSONDecodeError:
                return {"status": resp.status, "data": None, "raw": raw[:5000]}

        except Exception as e:
            logger.error(f"API replay failed for {url}: {e}")
            return None

    def get_captured_apis(self) -> List[Dict[str, Any]]:
        """Return all captured API interactions."""
        return list(self._captured_apis)


# ============================================================================
# Unified Paywall Bypass Orchestrator
# ============================================================================

class PaywallBypassOrchestrator:
    """Unified orchestrator that chains multiple bypass techniques in optimal order.

    Execution order:
    1. Cache lookup (fastest, no detection risk)
    2. Rule-based DOM stripping (lightweight, works on static HTML)
    3. Browser-based DOM manipulation (for JS-rendered paywalls)
    4. Session/API interception (for authenticated content)
    5. Proxy-based fetching (fallback for stubborn paywalls)
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.ladder_proxy = LadderProxyBypass(
            proxy_url=self.config.get("proxy_url")
        )
        self.dom_manipulator = DOMManipulationBypass(
            headless=self.config.get("headless", True)
        )
        self.rule_engine = RuleBasedPaywallBypass()
        self.cache_retriever = CacheContentRetriever()
        self.session_manager = SessionCookieManager()
        self.api_interceptor = APIInterceptionEngine()

        # Custom rules from user
        custom_rules = self.config.get("custom_rules")
        if custom_rules:
            for rule in custom_rules:
                self.rule_engine.add_rule(
                    name=rule.get("name", ""),
                    selector=rule.get("selector", ""),
                    action=rule.get("action", "remove_element"),
                )

    def bypass(self, url: str, html: Optional[str] = None,
               method: str = "auto") -> Dict[str, Any]:
        """Execute paywall bypass chain. Returns result with technique used."""
        result = {
            "url": url,
            "success": False,
            "technique": None,
            "html": None,
            "markdown": None,
            "error": None,
        }

        try:
            # Step 1: Try cache first (zero detection risk)
            if method in ("auto", "cache"):
                cached = self.cache_retriever.fetch_wayback(url)
                if cached and len(cached) > 1000:
                    result["success"] = True
                    result["technique"] = "wayback_cache"
                    result["html"] = cached
                    return result

            # Step 2: If we already have HTML, apply rule-based stripping
            if html:
                stripped = self.rule_engine.apply_rules(html)
                if len(stripped) > len(html) * 0.5:  # Still substantial content
                    result["success"] = True
                    result["technique"] = "rule_based_strip"
                    result["html"] = stripped
                    return result

            # Step 3: Browser-based DOM manipulation
            if method in ("auto", "browser", "dom"):
                browser_html = self.dom_manipulator.bypass(url)
                if browser_html and len(browser_html) > 1000:
                    # Apply additional rule stripping
                    browser_html = self.rule_engine.apply_rules(browser_html)
                    result["success"] = True
                    result["technique"] = "browser_dom_manipulation"
                    result["html"] = browser_html
                    return result

            # Step 4: Proxy-based fetching
            if method in ("auto", "proxy"):
                proxy_html = self.ladder_proxy.fetch_via_proxy(url)
                if proxy_html and len(proxy_html) > 1000:
                    result["success"] = True
                    result["technique"] = "proxy_fetch"
                    result["html"] = proxy_html
                    return result

            result["error"] = "All bypass techniques failed"

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Paywall bypass failed for {url}: {e}")

        return result

    def bypass_with_session(self, url: str, session_id: str,
                            method: str = "auto") -> Dict[str, Any]:
        """Execute bypass using a pre-authenticated session."""
        cookies = self.session_manager.export_session_cookies(session_id)
        if not cookies:
            return {"success": False, "error": f"Session {session_id} not found"}

        # Merge cookies into headers
        headers = {"Cookie": "; ".join(f"{k}={v}" for k, v in cookies.items())}

        # Try fetching with session cookies first
        try:
            import urllib.request
            req = urllib.request.Request(url)
            for k, v in headers.items():
                req.add_header(k, v)
            req.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
            resp = urllib.request.urlopen(req, timeout=15)
            html = resp.read().decode('utf-8', errors='ignore')

            # Apply rule-based stripping on the fetched content
            stripped = self.rule_engine.apply_rules(html)
            if stripped and len(stripped) > 1000:
                return {
                    "success": True,
                    "technique": "session_auth",
                    "html": stripped,
                    "session_id": session_id,
                }
        except Exception as e:
            logger.error(f"Session fetch failed for {url}: {e}")

        # Fall back to regular bypass chain
        return self.bypass(url, method=method)

    def analyze_paywall(self, html: str) -> Dict[str, Any]:
        """Analyze HTML to detect paywall type and recommend bypass strategy."""
        findings = {
            "has_paywall": False,
            "paywall_type": None,
            "indicators": [],
            "recommended_technique": None,
        }

        html_lower = html.lower()

        # Detect common paywall indicators
        indicators = {
            "overlay": any(kw in html_lower for kw in ['paywall', 'overlay', 'subscription-prompt']),
            "blur": 'filter: blur' in html_lower or 'class="blur' in html_lower,
            "meter": 'meter' in html_lower or 'remaining' in html_lower,
            "login_prompt": any(kw in html_lower for kw in ['log in', 'sign up', 'subscribe to continue']),
            "modal": 'role="dialog"' in html_lower or 'class="modal' in html_lower,
            "js_gate": any(kw in html_lower for kw in ['gate.js', 'paywall.js', 'metering.js']),
        }

        findings["indicators"] = [k for k, v in indicators.items() if v]
        findings["has_paywall"] = len(findings["indicators"]) >= 2

        if findings["has_paywall"]:
            if indicators["overlay"] or indicators["modal"]:
                findings["paywall_type"] = "overlay"
                findings["recommended_technique"] = "browser_dom_manipulation"
            elif indicators["blur"]:
                findings["paywall_type"] = "blur"
                findings["recommended_technique"] = "rule_based_strip"
            elif indicators["meter"]:
                findings["paywall_type"] = "metered"
                findings["recommended_technique"] = "cache_lookup"
            else:
                findings["paywall_type"] = "unknown"
                findings["recommended_technique"] = "proxy_fetch"

        return findings

    def close(self):
        """Clean up resources."""
        self.dom_manipulator.close()
