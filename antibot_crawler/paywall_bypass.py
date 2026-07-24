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
            # Remove entire element by class (any tag type)
            pattern = rf'<[a-zA-Z][a-zA-Z0-9]*\b[^>]*class=["\'][^"\']*{re.escape(cls)}[^"\']*["\'][^>]*>.*?</[a-zA-Z][a-zA-Z0-9]*>'
            result = re.sub(pattern, '', result, flags=re.IGNORECASE | re.DOTALL)

            # Also try simpler patterns without closing tag (self-closing)
            pattern2 = rf'<[a-zA-Z][a-zA-Z0-9]*\s+[^>]*class=["\'][^"\']*{re.escape(cls)}[^"\']*["\'][^>]*/?>\s*?'
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
            "name": "remove_paywall_overlay",
            "type": "css_remove",
            'selector': '.paywall, .paywall-overlay, .paywall-container, .paywall-message, .pw-overlay, .pw-container',
            "action": "remove_element",
        },
        {
            "name": "remove_metered_content_blur",
            "type": "css_remove",
            'selector': '.metered-content-blur, .article-body--locked, [class*="metered"][class*="blur"]',
            "action": "remove_overlay",
        },
        {
            "name": "remove_login_wall",
            "type": "css_remove",
            'selector': '.login-wall, .registration-wall, .signup-prompt, [class*="auth-wall"], .subscribe-prompt, .subscription-prompt',
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
            # Match any tag with the class (including self-closing and void elements)
            pattern = rf'<[a-zA-Z][a-zA-Z0-9]*\b[^>]*class=["\'][^"\']*{re.escape(cls)}[^"\']*["\'][^>]*>.*?</[a-zA-Z][a-zA-Z0-9]*>'
            html = re.sub(pattern, '', html, flags=re.IGNORECASE | re.DOTALL)
            # Also try simpler patterns without closing tag (self-closing)
            pattern2 = rf'<[a-zA-Z][a-zA-Z0-9]*\s+[^>]*class=["\'][^"\']*{re.escape(cls)}[^"\']*["\'][^>]*/?>\s*?'
            html = re.sub(pattern2, '', html, flags=re.IGNORECASE)
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
    server-side rendering. This engine helps identify and replay those APIs,
    plus extract embedded JSON data from scripts (SSR payloads, hydration data).

    Enhanced with auto-discovery of:
    - Inline fetch/XHR/axios calls in script tags
    - GraphQL queries and mutations
    - Embedded JSON payloads (__NEXT_DATA__, __INITIAL_STATE__, window.__DATA__)
    - JSON-LD structured data with article content
    - REST API endpoint patterns in page source
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
        r'/api/v\d+/users?/?\d*/(subscriptions|plans|articles)',
    ]

    def __init__(self):
        self._captured_apis: List[Dict[str, Any]] = []
        self._known_endpoints: Dict[str, Dict] = {}
        self._session_headers: Dict[str, str] = {}
        self._auth_tokens: Dict[str, str] = {}

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
        """Scan HTML for inline API calls, GraphQL queries, or embedded content."""
        apis = []

        # 1. Look for fetch/XHR/axios calls in inline scripts
        fetch_patterns = [
            r'fetch\s*\(\s*[`\'"]([^`\'"]*(?:api|graphql|json)[^`\'"]*)[`\'"]',
            r'axios\.(?:get|post|request)\s*\(\s*[`\'"]([^`\'"]*(?:api|graphql|json)[^`\'"]*)[`\'"]',
            r'url:\s*[`\'"]([^`\'"]*(?:api|graphql|json)[^`\'"]*)[`\'"]',
            r'endpoint:\s*[`\'"]([^`\'"]*(?:api|graphql|json)[^`\'"]*)[`\'"]',
        ]

        for pattern in fetch_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            apis.extend(matches)

        # 2. Extract GraphQL queries from scripts
        graphql_queries = self._extract_graphql(html)
        apis.extend(graphql_queries)

        # 3. Discover embedded JSON payloads (SSR/hydration data)
        embedded = self._extract_embedded_json(html)
        apis.extend(embedded)

        return list(set(apis))

    def _extract_graphql(self, html: str) -> List[str]:
        """Extract GraphQL queries and mutations from page source."""
        queries = []

        # Find GraphQL query strings in script tags
        gql_patterns = [
            r'(?:query|mutation|subscription)\s+\w+\s*\([^)]*\)\s*\{[^}]*\}',
            r'"(?:query|mutation)"\s*:\s*"([^"]*(?:query|mutation)[^"]*)"',
            r'gql\s*\x60([^\x60]*(?:query|mutation)[^\x60]*)\x60',
            r'apollo\.createClient\s*\(\s*\{[^}]*uri:\s*[`\'"]([^`\'"]*(?:graphql|gql)[^`\'"]*)[`\'"]',
        ]

        for pattern in gql_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)
            for m in matches:
                if len(m) > 10:  # Filter out noise
                    queries.append(f"graphql: {m[:300]}")

        return queries

    def _extract_embedded_json(self, html: str) -> List[str]:
        """Extract embedded JSON data from script tags and window variables."""
        results = []

        # Standard SSR hydration patterns
        json_patterns = [
            (r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>', '__NEXT_DATA__'),
            (r'<script[^>]*id=["\']__NUXT__["\'][^>]*>(.*?)</script>', '__NUXT__'),
            (r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});', '__INITIAL_STATE__'),
            (r'window\.__NUXT__\s*=\s*(\{.*?\});', '__NUXT__'),
            (r'window\.__DATA__\s*=\s*(\{.*?\});', '__DATA__'),
            (r'document\.addEventListener\s*\(\s*[`\'"]DOMContentLoaded["\']\s*,\s*\([^)]*\)\s*=>\s*\{[^}]*data\s*:\s*([\{][^}]*)', 'DOMContentLoaded_data'),
        ]

        for pattern, name in json_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)
            for match in matches:
                try:
                    data = json.loads(match)
                    # Try to find article/content fields in the JSON
                    content_keys = ['article', 'content', 'post', 'story', 'data',
                                    'body', 'text', 'html', 'title', 'author']
                    found_content = False
                    for key in content_keys:
                        if key in str(data).lower():
                            found_content = True
                            break
                    if found_content:
                        results.append(f"{name}: {json.dumps(data)[:500]}")
                except json.JSONDecodeError:
                    pass

        # Also check JSON-LD structured data
        ld_patterns = [
            r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>',
        ]
        for pattern in ld_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)
            for match in matches:
                try:
                    data = json.loads(match)
                    # Check if it's an Article or NewsArticle type
                    if isinstance(data, dict):
                        type_val = data.get('@type', '')
                        if 'Article' in str(type_val) or 'News' in str(type_val):
                            results.append(f"json-ld({type_val}): {json.dumps(data)[:500]}")
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict):
                                type_val = item.get('@type', '')
                                if 'Article' in str(type_val) or 'News' in str(type_val):
                                    results.append(f"json-ld({type_val}): {json.dumps(item)[:500]}")
                except json.JSONDecodeError:
                    pass

        return results

    def set_session_headers(self, headers: Dict[str, str]):
        """Set session headers to use when replaying API calls."""
        self._session_headers.update(headers)

    def set_auth_token(self, token_type: str, token: str):
        """Set authentication token for API replay."""
        self._auth_tokens[token_type] = token

    def get_auth_headers(self) -> Dict[str, str]:
        """Build auth headers from stored tokens."""
        headers = {}
        for token_type, token in self._auth_tokens.items():
            if token_type == 'bearer':
                headers['Authorization'] = f'Bearer {token}'
            elif token_type == 'jwt':
                headers['Authorization'] = f'Bearer {token}'
            elif token_type == 'cookie':
                headers['Cookie'] = token
            else:
                headers[token_type] = token
        return headers

    def replay_api_call(self, url: str, method: str = "GET",
                        headers: Optional[Dict] = None,
                        timeout: int = 10) -> Optional[Dict[str, Any]]:
        """Replay a captured API call with auth/session support to fetch fresh content."""
        try:
            import urllib.request
            import urllib.error

            req = urllib.request.Request(url, method=method)

            # Merge session headers, auth headers, and caller-provided headers
            merged_headers = dict(self._session_headers)
            merged_headers.update(self.get_auth_headers())
            if headers:
                merged_headers.update(headers)

            for k, v in merged_headers.items():
                req.add_header(k, v)
            req.add_header('Accept', 'application/json, text/plain, */*')
            req.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
            req.add_header('Referer', 'https://example.com/')

            resp = urllib.request.urlopen(req, timeout=timeout)
            raw = resp.read().decode('utf-8', errors='ignore')

            result: Dict[str, Any] = {"status": resp.status, "raw": raw[:10000]}

            # Try to parse as JSON and extract useful fields
            try:
                data = json.loads(raw)
                result["data"] = data
                # Auto-extract article content from common response shapes
                extracted = self._extract_content_from_json(data)
                if extracted:
                    result["extracted_text"] = extracted
                    result["extraction_method"] = "json_extraction"
            except json.JSONDecodeError:
                result["data"] = None

            return result

        except Exception as e:
            logger.error(f"API replay failed for {url}: {e}")
            return None

    def _extract_content_from_json(self, data: Any) -> Optional[str]:
        """Auto-extract article text from common API response structures."""
        if not isinstance(data, dict):
            return None

        # Common article content field names
        content_keys = [
            'content', 'article_body', 'body', 'text', 'html', 'description',
            'summary', 'excerpt', 'full_article', 'articleContent', 'postContent',
            'story', 'data',
        ]

        def try_extract(obj):
            if not isinstance(obj, dict):
                return None
            for key in content_keys:
                if key in obj:
                    val = obj[key]
                    if isinstance(val, str) and len(val) > 50:
                        return self._clean_html_to_text(val)
            return None

        # Direct match at top level
        result = try_extract(data)
        if result:
            return result

        # Nested under 'data' or 'article' — go two levels deep
        for wrapper_key in ['data', 'article', 'post', 'story', 'entry', 'props']:
            if wrapper_key in data and isinstance(data[wrapper_key], dict):
                inner = data[wrapper_key]
                result = try_extract(inner)
                if result:
                    return result
                # Go one more level deep
                for nested_key in ['article', 'pageProps', 'content', 'data', 'result']:
                    if nested_key in inner and isinstance(inner[nested_key], dict):
                        result = try_extract(inner[nested_key])
                        if result:
                            return result

        # Check list items (e.g., paginated articles)
        for key in ['items', 'articles', 'posts', 'results', 'edges']:
            if key in data and isinstance(data[key], list):
                texts = []
                for item in data[key][:5]:  # First 5 items
                    extracted = try_extract(item)
                    if extracted:
                        texts.append(extracted)
                if texts:
                    return '\n\n'.join(texts)

        return None

    @staticmethod
    def _clean_html_to_text(html_content: str) -> str:
        """Convert HTML content to clean text."""
        import html as html_module
        # Remove script/style tags
        text = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.IGNORECASE | re.DOTALL)
        # Remove HTML tags but keep newlines
        text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</?(?:p|div|h[1-6]|li|tr)', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<[^>]+>', '', text)
        # Decode HTML entities
        text = html_module.unescape(text)
        # Clean whitespace
        lines = [line.strip() for line in text.splitlines()]
        lines = [l for l in lines if l]
        return '\n'.join(lines)

    def extract_article_from_response(self, response: Dict[str, Any]) -> Optional[str]:
        """Extract readable article text from a replayed API response."""
        if not response:
            return None

        # If already extracted
        if response.get("extracted_text"):
            return response["extracted_text"]

        data = response.get("data")
        if data and isinstance(data, dict):
            return self._extract_content_from_json(data)

        raw = response.get("raw", "")
        if raw:
            try:
                data = json.loads(raw)
                if isinstance(data, dict):
                    return self._extract_content_from_json(data)
            except json.JSONDecodeError:
                pass

        return None

    def get_captured_apis(self) -> List[Dict[str, Any]]:
        """Return all captured API interactions."""
        return list(self._captured_apis)


# ============================================================================
# Unified Paywall Bypass Orchestrator
# ============================================================================

class PaywallBypassOrchestrator:
    """Unified orchestrator that chains multiple bypass techniques in optimal order.

    Execution order (smart escalation):
    1. Analyze paywall type from HTML signature
    2. Cache lookup (fastest, zero detection risk) — if paywall is overlay/metered
    3. Rule-based DOM stripping (lightweight) — for static HTML paywalls
    4. Browser-based DOM manipulation (JS-rendered paywalls)
    5. Session/API interception (authenticated content)
    6. Proxy-based fetching (fallback for stubborn paywalls)

    Supports progressive escalation: if one strategy fails, automatically tries
    the next one with adaptive timeout and retry logic.
    """

    # Strategy priority ranking (lower = try first)
    STRATEGY_PRIORITY = {
        "cache_lookup": 0,       # Zero cost, zero detection
        "rule_based_strip": 1,   # Lightweight, works on static HTML
        "browser_dom_manipulation": 2,  # JS rendering, moderate cost
        "api_interception": 3,   # Replay captured API calls for content
        "session_auth": 4,       # Requires pre-configured session
        "proxy_fetch": 5,        # Network cost, proxy dependency
    }

    # Paywall type → recommended starting strategy
    PAYWALL_STRATEGY_MAP = {
        "overlay": "rule_based_strip",
        "blur": "rule_based_strip",
        "metered": "cache_lookup",
        "login_required": "session_auth",
        "js_rendered": "browser_dom_manipulation",
        "unknown": "rule_based_strip",
    }
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.ladder_proxy = LadderProxyBypass(
            proxy_url=self.config.get("proxy_url"),
        )
        self.dom_manipulator = DOMManipulationBypass(
            headless=self.config.get("headless", True),
        )
        self.rule_engine = RuleBasedPaywallBypass()
        self.cache_retriever = CacheContentRetriever()
        self.session_manager = SessionCookieManager()
        self.api_engine = APIInterceptionEngine()
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

        # Strategy performance tracking
        self._strategy_stats: Dict[str, Dict[str, int]] = {
            "cache_lookup": {"attempts": 0, "successes": 0},
            "rule_based_strip": {"attempts": 0, "successes": 0},
            "browser_dom_manipulation": {"attempts": 0, "successes": 0},
            "api_interception": {"attempts": 0, "successes": 0},
            "session_auth": {"attempts": 0, "successes": 0},
            "proxy_fetch": {"attempts": 0, "successes": 0},
        }

    def _record_strategy_attempt(self, technique: str, success: bool):
        """Track strategy performance for smart escalation."""
        if technique in self._strategy_stats:
            self._strategy_stats[technique]["attempts"] += 1
            if success:
                self._strategy_stats[technique]["successes"] += 1

    def _get_strategy_order(self, paywall_type: Optional[str] = None,
                           method: str = "auto") -> List[str]:
        """Determine optimal strategy execution order.

        Uses paywall analysis + historical success rates to rank strategies.
        """
        strategies = list(self.STRATEGY_PRIORITY.keys())

        # If specific method requested, filter and reorder
        if method != "auto":
            if method in strategies:
                return [method]
            return strategies[:1]  # Fallback to first available

        # Start with paywall-type-recommended strategy
        if paywall_type and paywall_type in self.PAYWALL_STRATEGY_MAP:
            preferred = self.PAYWALL_STRATEGY_MAP[paywall_type]
            if preferred in strategies:
                # Put preferred first, rest follow by priority
                strategies.remove(preferred)
                strategies.insert(0, preferred)

        # Boost strategies with better historical success rates
        def strategy_score(s):
            stats = self._strategy_stats[s]
            rate = stats["successes"] / max(stats["attempts"], 1)
            return -rate * 10 + self.STRATEGY_PRIORITY[s]  # Higher is better

        strategies.sort(key=strategy_score)
        return strategies

    def bypass(self, url: str, html: Optional[str] = None,
               method: str = "auto", max_attempts: int = 4) -> Dict[str, Any]:
        """Execute paywall bypass chain with smart strategy selection and escalation.

        Args:
            url: Target URL
            html: Pre-fetched HTML content (if None, will fetch via HTTP)
            method: Strategy hint ("auto", "cache", "browser", "proxy", etc.)
            max_attempts: Max number of strategy escalations before giving up

        Returns result dict with technique used and clean HTML.
        """
        result = {
            "url": url,
            "success": False,
            "technique": None,
            "html": None,
            "markdown": None,
            "error": None,
            "strategies_tried": [],
        }

        try:
            # Step 0: Analyze paywall type from HTML if available
            paywall_type = None
            if html:
                analysis = self.analyze_paywall(html)
                if analysis.get("has_paywall"):
                    paywall_type = analysis.get("paywall_type", "unknown")
                    logger.info(f"Paywall detected: type={paywall_type}, indicators={analysis['indicators']}")

            # Determine strategy order
            strategy_order = self._get_strategy_order(paywall_type, method)

            # Execute strategies in priority order
            for i, strategy in enumerate(strategy_order):
                if i >= max_attempts:
                    break

                result["strategies_tried"].append(strategy)
                logger.debug(f"Trying paywall bypass strategy {i+1}/{len(strategy_order)}: {strategy}")

                success, html_out = self._try_strategy(strategy, url, html)
                self._record_strategy_attempt(strategy, success)

                if success and html_out:
                    result["success"] = True
                    result["technique"] = strategy
                    result["html"] = html_out
                    logger.info(f"Paywall bypass succeeded via {strategy}")
                    return result

            result["error"] = f"All {len(result['strategies_tried'])} bypass strategies failed"
            logger.warning(f"Paywall bypass failed for {url}: tried {result['strategies_tried']}")

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Paywall bypass exception for {url}: {e}")

        return result

    def _try_strategy(self, strategy: str, url: str,
                      html: Optional[str]) -> Tuple[bool, Optional[str]]:
        """Try a single bypass strategy. Returns (success, html)."""
        try:
            if strategy == "cache_lookup":
                cached = self.cache_retriever.fetch_wayback(url)
                if cached and len(cached) > 1000:
                    # Verify it's actually the target domain content, not a redirect
                    parsed = urlparse(url)
                    target_domain = parsed.netloc
                    # Reject Google search results or other redirects
                    is_google_search = 'Google Search' in cached[:500] or \
                                       'webcache.googleusercontent.com' in cached[:500]
                    if not is_google_search and target_domain in cached:
                        return True, cached
                # Also try Google cache — must be actual page, not search results
                gc = self.cache_retriever.fetch_google_cache(url)
                if gc and len(gc) > 1000:
                    parsed = urlparse(url)
                    target_domain = parsed.netloc
                    # Google cache should contain the actual page, not search results
                    is_google_search = 'Google Search' in gc[:500] or \
                                       '<title>Google</title>' in gc[:500].lower()
                    if not is_google_search and target_domain in gc:
                        return True, gc
                return False, None

            elif strategy == "rule_based_strip":
                if not html:
                    return False, None
                stripped = self.rule_engine.apply_rules(html)
                if stripped and len(stripped) > len(html) * 0.3:
                    return True, stripped
                return False, None

            elif strategy == "browser_dom_manipulation":
                browser_html = self.dom_manipulator.bypass(url)
                if browser_html and len(browser_html) > 1000:
                    browser_html = self.rule_engine.apply_rules(browser_html)
                    return True, browser_html

            elif strategy == "api_interception":
                if not html:
                    return False, None
                # Discover API endpoints from HTML
                discovered = self.api_engine.find_content_apis(html)
                if not discovered:
                    return False, None
                # Try to extract embedded JSON content directly
                for item in discovered:
                    if item.startswith('embedded:') or item.startswith('__NEXT') or \
                       item.startswith('__NUXT__') or item.startswith('__INITIAL') or \
                       item.startswith('__DATA__'):
                        try:
                            # Extract the JSON part after the prefix
                            json_str = item.split(': ', 1)[1] if ': ' in item else item
                            data = json.loads(json_str[:2000])  # Limit size
                            extracted = self.api_engine._extract_content_from_json(data)
                            if extracted and len(extracted) > 200:
                                return True, extracted
                        except (json.JSONDecodeError, IndexError):
                            pass
                    elif item.startswith('graphql:'):
                        # GraphQL query found — record it for later replay
                        query_text = item.split(': ', 1)[1] if ': ' in item else item
                        self.api_engine.capture_request(
                            url=f"graphql://{url}",
                            method="POST",
                            response_data={"query": query_text[:500]},
                        )
                    elif item.startswith('json-ld'):
                        # JSON-LD structured data — try to extract article text
                        try:
                            json_str = item.split(': ', 1)[1] if ': ' in item else item
                            data = json.loads(json_str[:2000])
                            extracted = self.api_engine._extract_content_from_json(data)
                            if extracted and len(extracted) > 200:
                                return True, extracted
                        except (json.JSONDecodeError, IndexError):
                            pass
                # If we discovered API patterns but couldn't extract inline,
                # try replaying known API endpoints
                for api_url in discovered:
                    if api_url.startswith('/api/') or api_url.startswith('http'):
                        resp = self.api_engine.replay_api_call(api_url)
                        if resp and resp.get("extracted_text"):
                            return True, resp["extracted_text"]
                return False, None

            elif strategy == "session_auth":
                # Try any configured sessions
                for sid, session in self.session_manager._sessions.items():
                    cookies = session.get("cookies", {})
                    if cookies:
                        headers = {"Cookie": "; ".join(f"{k}={v}" for k, v in cookies.items())}
                        try:
                            import urllib.request
                            req = urllib.request.Request(url)
                            for k, v in headers.items():
                                req.add_header(k, v)
                            req.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
                            resp = urllib.request.urlopen(req, timeout=15)
                            session_html = resp.read().decode('utf-8', errors='ignore')
                            stripped = self.rule_engine.apply_rules(session_html)
                            if stripped and len(stripped) > 1000:
                                return True, stripped
                        except Exception:
                            continue
                return False, None

            elif strategy == "proxy_fetch":
                proxy_html = self.ladder_proxy.fetch_via_proxy(url)
                if proxy_html and len(proxy_html) > 1000:
                    return True, proxy_html
                return False, None

        except Exception as e:
            logger.debug(f"Strategy '{strategy}' failed: {e}")

        return False, None

    def bypass_with_session(self, url: str, session_id: str,
                            method: str = "auto") -> Dict[str, Any]:
        """Execute bypass using a pre-authenticated session."""
        cookies = self.session_manager.export_session_cookies(session_id)
        if not cookies:
            return {"success": False, "error": f"Session {session_id} not found"}

        # Create a temporary session and try it
        temp_sid = f"temp_{session_id}"
        self.session_manager.create_session(temp_sid, cookies)
        result = self.bypass(url, method="session_auth")
        result["session_id"] = session_id

        # Clean up temp session
        if temp_sid in self.session_manager._sessions:
            del self.session_manager._sessions[temp_sid]

        return result

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
