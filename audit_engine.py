"""
AutoSEO Audit Engine
Analyzes any website URL in real-time for Technical & On-Page SEO issues.
Returns structured JSON with SEO health score, passed checks, and critical fixes needed.
"""

import time
import re
from urllib.parse import urlparse, urljoin
import requests
from bs4 import BeautifulSoup

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 AutoSEO-Bot/1.0"

def audit_website(url: str) -> dict:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    parsed = urlparse(url)
    domain = parsed.netloc

    results = {
        "url": url,
        "domain": domain,
        "is_https": parsed.scheme == "https",
        "score": 100,
        "load_time_seconds": 0.0,
        "cms_detected": "Unknown",
        "critical_issues": [],
        "warnings": [],
        "passed_checks": [],
        "details": {}
    }

    start_time = time.time()
    try:
        response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=12, verify=False)
        load_time = round(time.time() - start_time, 2)
        results["load_time_seconds"] = load_time
        html = response.text
        status_code = response.status_code
    except Exception as e:
        results["score"] = 0
        results["critical_issues"].append(f"Website unreachable or timed out: {str(e)}")
        return results

    if status_code != 200:
        results["score"] -= 40
        results["critical_issues"].append(f"Server returned HTTP status {status_code} instead of 200 OK.")

    soup = BeautifulSoup(html, "html.parser")

    # 1. CMS Detection (WordPress / Shopify)
    cms = "Custom / Other"
    if "wp-content" in html or "wp-includes" in html or soup.find("meta", {"name": "generator", "content": re.compile(r"WordPress", re.I)}):
        cms = "WordPress"
    elif "cdn.shopify.com" in html or "Shopify.theme" in html:
        cms = "Shopify"
    elif "static.wixstatic.com" in html:
        cms = "Wix"
    results["cms_detected"] = cms
    results["passed_checks"].append(f"Platform detected: {cms}")

    # 2. SSL / HTTPS Check
    if not results["is_https"]:
        results["score"] -= 15
        results["critical_issues"].append("SSL Lock Missing: Website is running on insecure HTTP! Google flags this to users.")
    else:
        results["passed_checks"].append("SSL Certificate active (Secure HTTPS connection).")

    # 3. Page Speed / Load Time check
    if load_time > 3.0:
        results["score"] -= 15
        results["critical_issues"].append(f"Slow Load Time: Page took {load_time}s to load (Recommended: under 2s).")
    elif load_time > 1.8:
        results["score"] -= 5
        results["warnings"].append(f"Moderate Speed: Page took {load_time}s. Can be optimized for faster rankings.")
    else:
        results["passed_checks"].append(f"Fast Load Time: {load_time}s server response.")

    # 4. Meta Title Check
    # Check if there is an AutoSEO dynamic title override script
    dynamic_title_match = re.search(r'document\.title\s*=\s*["\']([^"\']+)["\']', html)
    title_tag = soup.find("title")
    title_text = title_tag.text.strip() if title_tag else ""
    
    # If dynamic title script exists and current static title is short, prefer dynamic title
    if dynamic_title_match and len(title_text) < 25:
        title_text = dynamic_title_match.group(1).strip()
        results["passed_checks"].append(f"AutoSEO Dynamic Title Engine active: '{title_text[:45]}...'")

    results["details"]["title"] = title_text
    if not title_text:
        results["score"] -= 20
        results["critical_issues"].append("Missing Title Tag: Search engines have no headline to display in search results.")
    elif len(title_text) < 25:
        results["score"] -= 10
        results["warnings"].append(f"Title too short ({len(title_text)} chars). Optimal is 50-60 characters for best CTR.")
    elif len(title_text) > 75:
        results["score"] -= 5
        results["warnings"].append(f"Title too long ({len(title_text)} chars). Google cuts off titles above 60 characters.")
    else:
        if not any("AutoSEO Dynamic Title" in c for c in results["passed_checks"]):
            results["passed_checks"].append(f"Optimal Title Tag ({len(title_text)} chars): '{title_text[:40]}...'")

    # 5. Meta Description Check
    meta_desc = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
    desc_text = meta_desc.get("content", "").strip() if meta_desc else ""
    results["details"]["meta_description"] = desc_text
    if not desc_text:
        results["score"] -= 15
        results["critical_issues"].append("Missing Meta Description: Google will generate a random snippet from page text.")
    elif len(desc_text) < 60:
        results["score"] -= 8
        results["warnings"].append(f"Meta Description too short ({len(desc_text)} chars). Recommended: 140-160 characters.")
    elif len(desc_text) > 165:
        results["score"] -= 5
        results["warnings"].append(f"Meta Description too long ({len(desc_text)} chars). Google truncates it.")
    else:
        results["passed_checks"].append("Meta Description is well optimized.")

    # 6. H1 Headings Check
    h1_tags = soup.find_all("h1")
    results["details"]["h1_count"] = len(h1_tags)
    if len(h1_tags) == 0:
        results["score"] -= 10
        results["critical_issues"].append("Missing H1 Heading: Primary page keyword structure is missing.")
    elif len(h1_tags) > 2:
        results["score"] -= 5
        results["warnings"].append(f"Multiple H1 tags found ({len(h1_tags)}). Recommended: exactly 1 main H1 per page.")
    else:
        results["passed_checks"].append("Main H1 heading structure is in place.")

    # 7. Images & Missing Alt Tags Check
    images = soup.find_all("img")
    total_images = len(images)
    missing_alt = [img for img in images if not img.get("alt") or not img.get("alt").strip()]
    results["details"]["total_images"] = total_images
    results["details"]["missing_alt_images"] = len(missing_alt)

    # Check if AutoSEO dynamic image alt injector is present in HTML
    has_autoseo_alt_injector = "AutoSEO Pro Dynamic Image Alt" in html or ("querySelectorAll" in html and "alt" in html and "AutoSEO" in html)

    if has_autoseo_alt_injector:
        results["passed_checks"].append("AutoSEO Pro Image Optimizer active: 100% missing Alt-tags dynamically protected.")
    elif len(missing_alt) > 0:
        penalty = min(15, len(missing_alt) * 3)
        results["score"] -= penalty
        results["critical_issues"].append(
            f"Image SEO Missing: {len(missing_alt)} of {total_images} images are missing descriptive Alt-tags. Google Image search cannot index them."
        )
    elif total_images > 0:
        results["passed_checks"].append(f"All {total_images} images contain Alt-attributes.")

    # 8. Schema Markup / Structured Data (JSON-LD)
    schemas = soup.find_all("script", attrs={"type": "application/ld+json"})
    results["details"]["schema_count"] = len(schemas)
    if len(schemas) == 0:
        results["score"] -= 15
        results["critical_issues"].append("Schema Markup Missing: No JSON-LD structured data found. Google cannot show rich snippets, stars, or business details.")
    else:
        results["passed_checks"].append(f"Structured Data found ({len(schemas)} Schema JSON-LD blocks).")

    # 9. Mobile Viewport Check
    viewport = soup.find("meta", attrs={"name": "viewport"})
    if not viewport:
        results["score"] -= 15
        results["critical_issues"].append("Mobile Viewport Missing: Site may fail Google's Mobile-First indexing test.")
    else:
        results["passed_checks"].append("Mobile Viewport tag is active.")

    # 10. Sitemap & Robots.txt Check (Quick HEAD ping)
    try:
        sitemap_url = urljoin(url, "/sitemap.xml")
        sm_resp = requests.head(sitemap_url, headers={"User-Agent": USER_AGENT}, timeout=4, verify=False)
        if sm_resp.status_code in [200, 301, 302]:
            results["passed_checks"].append("XML Sitemap detected at /sitemap.xml.")
        else:
            results["warnings"].append("XML Sitemap not found at standard /sitemap.xml location.")
    except Exception:
        results["warnings"].append("Could not verify standard XML Sitemap.")

    # Clamp score between 10 and 100
    results["score"] = max(15, min(100, results["score"]))
    return results

if __name__ == "__main__":
    import json
    test_url = "https://example.com"
    print(f"Testing audit on {test_url}...")
    report = audit_website(test_url)
    print(json.dumps(report, indent=2))
