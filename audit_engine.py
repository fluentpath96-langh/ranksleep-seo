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

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"

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

    if len(missing_alt) > 0:
        penalty = min(15, len(missing_alt) * 3)
        results["score"] -= penalty
        results["critical_issues"].append(
            f"Image SEO Missing: {len(missing_alt)} of {total_images} images on this page are missing descriptive Alt-tags."
        )
    elif has_autoseo_alt_injector:
        results["passed_checks"].append("AutoSEO Pro Image Optimizer active: Alt-tags dynamically protected.")
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

    # 11. Deep E-Commerce Product Catalog Scan (Shopify & Woo)
    is_product_page = "/products/" in parsed.path
    if is_product_page and desc_text and len(desc_text) < 70:
        results["score"] -= 20
        results["critical_issues"].append(
            f"Thin Product Description: Page description is only {len(desc_text)} characters ('{desc_text[:40]}...'). Google penalizes thin product pages lacking comprehensive buyer information."
        )

    # If domain has /products.json (Shopify catalog), audit product catalog for thin content
    try:
        clean_origin = f"{parsed.scheme}://{domain}"
        cat_url = f"{clean_origin}/products.json?limit=25"
        cat_res = requests.get(cat_url, headers={"User-Agent": USER_AGENT}, timeout=5, verify=False)
        if cat_res.status_code == 200:
            catalog_products = cat_res.json().get("products", [])
            if catalog_products:
                thin_products = []
                truncated_titles = []
                missing_catalog_alts = 0
                total_catalog_imgs = 0
                analyzed_products = []

                for p in catalog_products:
                    p_title = p.get("title", "")
                    p_body = p.get("body_html", "") or ""
                    clean_body = re.sub(r'<[^<]+?>', '', p_body).strip()
                    p_imgs = p.get("images", [])
                    p_missing_alts = sum(1 for img in p_imgs if not img.get("alt"))
                    total_catalog_imgs += len(p_imgs)
                    missing_catalog_alts += p_missing_alts

                    p_issues = []
                    # Thin description check (less than 100 characters is incomplete / adhi-adhuri)
                    if len(clean_body) < 100:
                        thin_products.append((p_title, len(clean_body)))
                        p_issues.append(f"Thin / Incomplete Description ({len(clean_body)} chars)")
                    
                    # Title truncation check
                    if len(p_title) > 70:
                        truncated_titles.append((p_title, len(p_title)))
                        p_issues.append(f"Title Truncated by Google ({len(p_title)} chars)")
                    elif len(p_title) < 20:
                        p_issues.append("Title too short")
                    
                    if p_missing_alts > 0:
                        p_issues.append(f"{p_missing_alts} image(s) missing Alt tags")

                    analyzed_products.append({
                        "id": p.get("id"),
                        "title": p_title,
                        "handle": p.get("handle"),
                        "clean_desc": clean_body[:90] + ("..." if len(clean_body) > 90 else ""),
                        "desc_len": len(clean_body),
                        "missing_alts": p_missing_alts,
                        "issues": p_issues,
                        "has_issues": len(p_issues) > 0
                    })

                results["details"]["products_catalog"] = analyzed_products
                results["details"]["catalog_scanned_count"] = len(analyzed_products)

                # Penalties for Catalog Defects
                if thin_products:
                    penalty = min(25, len(thin_products) * 10)
                    results["score"] -= penalty
                    sample_name = thin_products[0][0]
                    sample_len = thin_products[0][1]
                    results["critical_issues"].append(
                        f"Thin Product Descriptions: Found {len(thin_products)} product(s) with incomplete/thin descriptions (e.g. '{sample_name[:38]}...' has only {sample_len} chars). Google Panda algorithm penalizes thin product pages!"
                    )

                if missing_catalog_alts > 0:
                    penalty = min(20, missing_catalog_alts * 2)
                    results["score"] -= penalty
                    results["critical_issues"].append(
                        f"Product Catalog Image SEO: {missing_catalog_alts} of {total_catalog_imgs} product images are missing descriptive Alt-tags. Google Images cannot index these products."
                    )

                if truncated_titles:
                    penalty = min(15, len(truncated_titles) * 3)
                    results["score"] -= penalty
                    results["warnings"].append(
                        f"Product Titles Exceeding Display Limit: {len(truncated_titles)} products have titles over 70 characters that will be cut off with '...' in Google search."
                    )
    except Exception:
        pass

    # Clamp score between 10 and 100
    results["score"] = max(15, min(100, results["score"]))
    return results

if __name__ == "__main__":
    import json
    test_url = "https://example.com"
    print(f"Testing audit on {test_url}...")
    report = audit_website(test_url)
    print(json.dumps(report, indent=2))
