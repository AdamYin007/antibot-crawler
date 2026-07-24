"""Anti-bot detection, CAPTCHA solving, proxy rotation, and behavior simulation."""
import hashlib
import json
import logging
import random
import re
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)


class AntiBotDetector:
    """Detects which anti-bot system is protecting a website."""
    
    SIGNATURES = {
        "cloudflare": [
            ("set_cookie", "cf_clearance"),
            ("set_cookie", "__cfduid"),
            ("body_contains", "cdn-cgi/challenge-platform"),
            ("body_contains", "cf-browser-verification"),
            ("body_contains", "captcha-box"),
            ("body_contains", "raysId"),
            ("body_contains", "CloudFront"),
        ],
        "akamai": [
            ("body_contains", "ak_bmsc"),
            ("body_contains", "bm_sz"),
            ("body_contains", "akamai"),
            ("body_contains", "AkamaiGHost"),
        ],
        "datadome": [
            ("body_contains", "datadome"),
            ("body_contains", "__ddid"),
            ("header_contains", "datadome"),
        ],
        "kasada": [
            ("body_contains", "kasada"),
            ("body_contains", "x-kasada"),
            ("body_contains", "kasada-challenge"),
        ],
        "perimeterx": [
            ("body_contains", "px-captcha"),
            ("body_contains", "perimeterx"),
            ("body_contains", "_pxvid"),
            ("body_contains", "_pxe"),
        ],
        "recaptcha": [
            ("body_contains", "g-recaptcha"),
            ("body_contains", "recaptcha/api.js"),
        ],
        "hcaptcha": [
            ("body_contains", "h-captcha"),
            ("body_contains", "hcaptcha.com"),
        ],
    }
    
    @classmethod
    def detect(cls, status_code: int, content: str, headers: Dict[str, str]) -> List[str]:
        """Analyze response to detect anti-bot systems in use."""
        detected = []
        body_lower = content.lower()
        set_cookie_header = headers.get("set-cookie", "").lower()
        
        for system, signatures in cls.SIGNATURES.items():
            if system in ("recaptcha", "hcaptcha"):
                continue
            
            for check_type, pattern in signatures:
                if check_type == "body_contains" and pattern.lower() in body_lower:
                    detected.append(system)
                    break
                elif check_type == "set_cookie" and pattern.lower() in set_cookie_header:
                    detected.append(system)
                    break
                elif check_type == "header_contains" and pattern.lower() in set_cookie_header:
                    detected.append(system)
                    break
        
        # Check CAPTCHAs
        if "g-recaptcha" in body_lower or "recaptcha" in body_lower:
            detected.append("recaptcha")
        if "h-captcha" in body_lower or "hcaptcha" in body_lower:
            detected.append("hcaptcha")
        
        return detected if detected else ["unknown"]
    
    @classmethod
    def get_recommendations(cls, detected_systems: List[str]) -> List[str]:
        """Get recommended countermeasures for detected anti-bot systems."""
        recommendations = {
            "cloudflare": [
                "Use stealth browser mode with patchright",
                "Enable Cloudflare challenge solving",
                "Rotate residential proxies",
                "Implement proper TLS fingerprinting",
                "Add realistic human behavior simulation",
            ],
            "akamai": [
                "Use enterprise-grade stealth mode",
                "Implement behavioral analysis mimicry",
                "Consider dedicated IP pool",
            ],
            "datadome": [
                "Use advanced browser fingerprint spoofing",
                "Implement session persistence",
                "Rotate user agents per session",
            ],
            "kasada": [
                "Use real browser automation with stealth plugins",
                "Implement network request interception",
                "Consider API endpoint discovery",
            ],
            "perimeterx": [
                "Use persistent browser sessions",
                "Implement proper cookie handling",
                "Add device fingerprint consistency",
            ],
            "recaptcha": [
                "Integrate CAPTCHA solving service (2Captcha/Anti-Captcha)",
                "Use headful browser mode for CAPTCHA pages",
                "Implement retry logic after CAPTCHA solving",
            ],
            "hcaptcha": [
                "Integrate CAPTCHA solving service",
                "Use headful browser mode",
            ],
        }
        
        recs = []
        for system in detected_systems:
            recs.extend(recommendations.get(system, []))
        
        # Deduplicate while preserving order
        return list(dict.fromkeys(recs))


class CaptchaSolver:
    """Integration with third-party CAPTCHA solving services."""
    
    def __init__(self, service: str, api_key: str):
        self.service = service
        self.api_key = api_key
    
    def solve_recaptcha(self, site_key: str, page_url: str) -> Optional[str]:
        """Solve Google reCAPTCHA v2/v3."""
        try:
            if self.service == "2captcha":
                return self._solve_2captcha("recaptcha", {
                    "googlekey": site_key,
                    "pageurl": page_url,
                    "version": "v2",
                })
        except Exception as e:
            logger.error(f"Captcha solving failed: {e}")
        return None
    
    def _solve_2captcha(self, task_type: str, params: Dict) -> Optional[str]:
        """Solve via 2Captcha API."""
        try:
            import urllib.request
            import urllib.parse
            
            url = "https://2captcha.com/in.php"
            data = f"key={self.api_key}&method=userrecaptcha&{urllib.parse.urlencode(params)}".encode()
            req = urllib.request.Request(url, data=data)
            resp = urllib.request.urlopen(req, timeout=30)
            result = resp.read().decode()
            
            if result.startswith("OK|"):
                captcha_id = result.split("|")[1]
                for _ in range(60):
                    time.sleep(5)
                    check_url = f"https://2captcha.com/res.php?key={self.api_key}&action=get&id={captcha_id}"
                    check_resp = urllib.request.urlopen(check_url, timeout=10)
                    check_result = check_resp.read().decode()
                    if check_result.startswith("OK|"):
                        return check_result.split("|")[1]
                    elif "BUSY" in check_result or "WAIT" in check_result:
                        continue
                    else:
                        return None
        except Exception as e:
            logger.error(f"2Captcha error: {e}")
        return None


class ProxyRotator:
    """Smart proxy rotator with automatic failover."""
    
    def __init__(self, proxies: List, health_check_interval: int = 300):
        self.proxies = list(proxies)
        self.health_check_interval = health_check_interval
        self._current_index = 0
        self._failed_proxies: Dict[str, float] = {}
    
    def get_next_proxy(self) -> Optional[Any]:
        """Get the next healthy proxy, rotating through the pool."""
        if not self.proxies:
            return None
        
        now = time.time()
        self._failed_proxies = {
            k: v for k, v in self._failed_proxies.items()
            if now - v < self.health_check_interval
        }
        
        for _ in range(len(self.proxies)):
            proxy = self.proxies[self._current_index % len(self.proxies)]
            self._current_index += 1
            if hasattr(proxy, 'url'):
                proxy_url = proxy.url
            else:
                proxy_url = str(proxy)
            
            if proxy_url not in self._failed_proxies:
                return proxy
        
        return self.proxies[0] if self.proxies else None
    
    def mark_failed(self, proxy_config):
        """Mark a proxy as failed."""
        if hasattr(proxy_config, 'url'):
            self._failed_proxies[proxy_config.url] = time.time()
    
    def mark_healthy(self, proxy_config):
        """Mark a proxy as healthy again."""
        if hasattr(proxy_config, 'url'):
            self._failed_proxies.pop(proxy_config.url, None)


class BehaviorSimulator:
    """Simulates human browsing behavior to avoid detection."""
    
    @staticmethod
    def random_delay(min_delay: float = 0.5, max_delay: float = 2.0):
        """Add a random delay between requests."""
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)
        return delay
    
    @staticmethod
    def generate_scroll_pattern(page, distance: int = 1000, steps: int = 10):
        """Generate realistic scrolling behavior."""
        if not page or not hasattr(page, 'evaluate'):
            return
        
        js_code = """
        (distance, steps) => {
            for (let i = 0; i <= steps; i++) {
                setTimeout(() => {
                    window.scrollBy(0, Math.floor(distance / steps) + Math.floor(Math.random() * 20 - 10));
                }, i * (50 + Math.random() * 100));
            }
        }
        """
        try:
            page.evaluate(js_code, distance, steps)
        except Exception:
            pass
    
    @staticmethod
    def generate_mouse_movement(page, start_x: int = 0, start_y: int = 0,
                                end_x: int = 800, end_y: int = 600, steps: int = 20):
        """Generate realistic mouse movement on a page."""
        if not page or not hasattr(page, 'evaluate'):
            return
        
        movements = []
        for i in range(steps + 1):
            t = i / steps
            x = start_x + (end_x - start_x) * t + random.gauss(0, 5)
            y = start_y + (end_y - start_y) * t + random.gauss(0, 5)
            movements.append({"x": max(0, x), "y": max(0, y)})
        
        js_code = """
        (movements) => {
            movements.forEach((pos, i) => {
                const event = new MouseEvent('mousemove', {
                    clientX: pos.x, clientY: pos.y, bubbles: true
                });
                document.body.dispatchEvent(event);
            });
            const last = movements[movements.length-1];
            document.body.dispatchEvent(new MouseEvent('mousedown', {
                clientX: last.x, clientY: last.y, bubbles: true
            }));
        }
        """
        try:
            page.evaluate(js_code, movements)
        except Exception:
            pass


class AdaptiveSelector:
    """Selectors that survive website structure changes using similarity matching."""
    
    def compute_element_signature(self, element: Dict[str, Any]) -> str:
        """Create a fingerprint for an element based on its properties."""
        props = {
            "tag": element.get("tag", ""),
            "text": element.get("text", "")[:50],
            "classes": sorted(element.get("classes", [])),
        }
        sig = json.dumps(props, sort_keys=True)
        return hashlib.md5(sig.encode()).hexdigest()
    
    def find_similar_elements(self, target_elements: List[Dict],
                               candidates: List[Dict],
                               threshold: float = 0.7) -> List[Dict]:
        """Find elements similar to targets using text and structural similarity."""
        results = []
        for target in target_elements:
            best_match = None
            best_score = 0
            
            for candidate in candidates:
                score = self._similarity_score(target, candidate)
                if score > best_score and score >= threshold:
                    best_score = score
                    best_match = candidate
            
            if best_match:
                results.append(best_match)
        
        return results
    
    def _similarity_score(self, a: Dict, b: Dict) -> float:
        """Calculate similarity between two elements."""
        score = 0.0
        
        # Text similarity
        text_a = a.get("text", "").lower().strip()
        text_b = b.get("text", "").lower().strip()
        if text_a and text_b:
            words_a = set(text_a.split())
            words_b = set(text_b.split())
            if words_a & words_b:
                intersection = len(words_a & words_b)
                union = len(words_a | words_b)
                score += 0.6 * (intersection / union) if union > 0 else 0
        
        # Tag match
        if a.get("tag") == b.get("tag"):
            score += 0.2
        
        # Class similarity
        classes_a = set(a.get("classes", []))
        classes_b = set(b.get("classes", []))
        if classes_a and classes_b:
            intersection = len(classes_a & classes_b)
            union = len(classes_a | classes_b)
            score += 0.2 * (intersection / union) if union > 0 else 0
        
        return score


class RobotsParser:
    """Simple robots.txt parser for respecting crawling rules."""
    
    def __init__(self):
        self._cache: Dict[str, str] = {}
    
    def can_fetch(self, url: str, user_agent: str = "*") -> bool:
        """Check if a URL can be fetched according to robots.txt."""
        parsed = urlparse(url)
        domain = parsed.netloc
        path = parsed.path
        
        robots_url = f"{parsed.scheme}://{domain}/robots.txt"
        
        if robots_url not in self._cache:
            try:
                import urllib.request
                req = urllib.request.Request(robots_url, headers={"User-Agent": "AntiBotCrawler/1.0"})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    self._cache[robots_url] = resp.read().decode("utf-8", errors="ignore")
            except Exception:
                return True
        
        return self._parse_and_check(self._cache[robots_url], path, user_agent)
    
    def _parse_and_check(self, content: str, path: str, user_agent: str) -> bool:
        """Parse robots.txt content and check if path is allowed."""
        disallow_paths = []
        current_ua = None
        
        for line in content.splitlines():
            line = line.strip()
            if line.lower().startswith("user-agent:"):
                current_ua = line.split(":", 1)[1].strip()
            elif line.lower().startswith("disallow:") and current_ua in (user_agent, "*"):
                path_val = line.split(":", 1)[1].strip()
                if path_val:
                    disallow_paths.append(path_val)
        
        for pattern in disallow_paths:
            if path.startswith(pattern):
                return False
        
        return True
