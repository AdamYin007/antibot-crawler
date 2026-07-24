# Paywall Bypass — Debugging Pitfalls & Fixes

## Cache Lookup False Positives

**Bug**: Wayback Machine and Google cache can return search result pages (e.g., Google Search results) for non-existent URLs, not the actual cached page content.

**Symptom**: `cache_lookup` strategy succeeds but returns irrelevant HTML (90K+ chars of Google search results instead of the target article).

**Fix**: After fetching cached content, validate it's actually the target domain's content:
1. Check that the response doesn't contain "Google Search" or "webcache.googleusercontent.com" in first 500 chars
2. Verify the target domain appears in the response body
3. Reject if it looks like a search results page

```python
is_google_search = 'Google Search' in cached[:500] or \
                   'webcache.googleusercontent.com' in cached[:500]
if not is_google_search and target_domain in cached:
    return True, cached
```

## Regex Tag Matching Too Narrow

**Bug**: `_remove_by_selector()` originally only matched `<div|section|article|main|header|footer>` tags, missing paywall elements on other tag types.

**Symptom**: Rule-based stripping fails to remove `.paywall-overlay`, `.login-wall`, etc. when they're on unexpected tag types.

**Fix**: Match any HTML tag type:
```python
pattern = rf'<[a-zA-Z][a-zA-Z0-9]*\b[^>]*class=["\'][^"\']*{re.escape(cls)}[^"\']*["\'][^>]*>.*?</[a-zA-Z][a-zA-Z0-9]*>'
```
Also handle self-closing tags with a second pattern.

## curl_cffi Impersonate Enum Mismatch

**Bug**: `ImpersonateTarget.CHROME_133` maps to `"chrome133"` which may not be supported by all curl_cffi versions.

**Symptom**: `AttributeError: Impersonating chrome133 is not supported` or `CHROME_133` enum value doesn't exist.

**Fix**: Add canonical short names (`CHROME="chrome"`, `FIREFOX="firefox"`, etc.) alongside versioned aliases. Default to the simple name.

## Default Rules Missing Generic Overlays

**Bug**: `RuleBasedPaywallBypass.DEFAULT_RULES` didn't include generic `.paywall-overlay` or `.pw-container` selectors.

**Symptom**: Common paywall overlay classes go unstripped.

**Fix**: Add a `remove_paywall_overlay` rule at the top of DEFAULT_RULES covering: `.paywall, .paywall-overlay, .paywall-container, .paywall-message, .pw-overlay, .pw-container`. Also expand login-wall rule to include `.subscribe-prompt, .subscription-prompt`.
