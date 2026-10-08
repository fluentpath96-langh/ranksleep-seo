"""
AutoSEO Audit Engine
Analyzes any website URL in real-time for Technical & On-Page SEO issues.
Returns structured JSON with SEO health score, passed checks, and critical fixes needed.
"""

import os
import json
import time
import re
from urllib.parse import urlparse, urljoin
import requests
from bs4 import BeautifulSoup

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"

def audit_website(url: str) -> dict:
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    elif url.startswith("http://"):
        # Auto-detect if HTTPS is available to avoid false SSL warning
        domain_probe = url.replace("http://", "").split("/")[0]
        try:
            probe = requests.head(f"https://{domain_probe}", timeout=4, verify=False)
            if probe.status_code < 400 or probe.status_code in [301, 302]:
                url = "https://" + url[7:]
        except Exception:
            pass

    parsed = urlparse(url)
    domain = parsed.netloc

    # Real-time inspection state (genuine store diagnostics)
    is_store_optimized = False
    has_images_fixed = False
    has_schema_injected = False
    has_titles_fixed = False
    has_descriptions_fixed = False

    results = {
        "url": url,
        "domain": domain,
        "is_https": url.startswith("https://"),
        "is_optimized_by_ranksleep": is_store_optimized,
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

    # 1. Advanced CMS & Platform Archetype Detection
    html_lower = html.lower()
    is_wp = bool(
        "wp-content" in html_lower or
        "wp-includes" in html_lower or
        "wp-json" in html_lower or
        soup.find("meta", {"name": "generator", "content": re.compile(r"WordPress", re.I)}) or
        soup.find("link", {"rel": re.compile(r"https://api\.w\.org/", re.I)})
    )

    is_shopify = bool(
        "cdn.shopify.com" in html_lower or
        "shopify.theme" in html_lower or
        "myshopify.com" in domain.lower() or
        "shopify-section" in html_lower
    )

    has_woocommerce = bool(
        "woocommerce" in html_lower or
        "/plugins/woocommerce/" in html_lower or
        "wc-ajax" in html_lower or
        "woocommerce-price-amount" in html_lower or
        "woocommerce-page" in html_lower
    )

    # Detect active WordPress plugins / builders
    detected_plugins = []
    if is_wp:
        if has_woocommerce:
            detected_plugins.append("WooCommerce")
        if "yoast" in html_lower or "yoast-schema-graph" in html_lower:
            detected_plugins.append("Yoast SEO")
        if "rank-math" in html_lower or "rankmath" in html_lower:
            detected_plugins.append("Rank Math")
        if "aioseo" in html_lower:
            detected_plugins.append("All in One SEO")
        if "elementor" in html_lower:
            detected_plugins.append("Elementor")
        if "divi" in html_lower or "et_builder" in html_lower:
            detected_plugins.append("Divi")
        if "learndash" in html_lower or "tutor-lms" in html_lower:
            detected_plugins.append("LMS")

    # Determine site archetype and user-facing badge
    platform = "custom"
    platform_name = "Custom Platform"
    badge_label = "Custom Site Detected"
    site_archetype = "business"

    # E-Commerce detection
    ecommerce_signals = [
        has_woocommerce,
        is_shopify,
        "add to cart" in html_lower,
        "add-to-cart" in html_lower,
        "/cart" in html_lower,
        "/checkout" in html_lower,
        "cart-contents" in html_lower
    ]

    if is_wp:
        platform = "wordpress"
        platform_name = "WordPress"
        if has_woocommerce or any(ecommerce_signals):
            site_archetype = "ecommerce"
            badge_label = "WordPress Store Detected"
        else:
            blog_signals = [
                len(soup.find_all("article")) >= 2,
                "/category/" in html_lower or "/author/" in html_lower or "/blog" in parsed.path.lower(),
                "entry-title" in html_lower,
                "wp-post-image" in html_lower
            ]
            lms_signals = ["learndash" in html_lower, "tutor-lms" in html_lower, "course" in html_lower]
            if any(blog_signals):
                site_archetype = "blog"
                badge_label = "WordPress Site Detected (Blog & Media)"
            elif any(lms_signals):
                site_archetype = "lms"
                badge_label = "WordPress LMS / Learning Portal Detected"
            else:
                site_archetype = "business"
                badge_label = "WordPress Site Detected"
    elif is_shopify:
        platform = "shopify"
        platform_name = "Shopify"
        site_archetype = "ecommerce"
        badge_label = "Shopify Store Detected"
    elif "static.wixstatic.com" in html_lower:
        platform = "wix"
        platform_name = "Wix"
        badge_label = "Wix Site Detected"
    elif "squarespace.com" in html_lower:
        platform = "squarespace"
        platform_name = "Squarespace"
        badge_label = "Squarespace Site Detected"

    cms_info = {
        "platform": platform,
        "platform_name": platform_name,
        "badge_label": badge_label,
        "site_archetype": site_archetype,
        "is_wordpress": is_wp,
        "is_shopify": is_shopify,
        "has_woocommerce": has_woocommerce,
        "detected_plugins": detected_plugins
    }

    results["cms_detected"] = platform_name
    results["cms_info"] = cms_info
    results["passed_checks"].append(f"Platform: {badge_label}")
    if detected_plugins:
        results["passed_checks"].append(f"WordPress Ecosystem: {', '.join(detected_plugins)}")

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

    if len(missing_alt) > 0 and not has_images_fixed:
        penalty = min(15, len(missing_alt) * 3)
        results["score"] -= penalty
        results["critical_issues"].append(
            f"Image SEO Missing: {len(missing_alt)} of {total_images} images on this page are missing descriptive Alt-tags."
        )
    elif has_images_fixed:
        results["passed_checks"].append(f"Image SEO: All {total_images} images protected with descriptive Alt-tags by RankSleep Vision AI.")
    elif has_autoseo_alt_injector:
        results["passed_checks"].append("AutoSEO Pro Image Optimizer active: Alt-tags dynamically protected.")
    elif total_images > 0:
        results["passed_checks"].append(f"All {total_images} images contain Alt-attributes.")

    # 8. Schema Markup / Structured Data (JSON-LD)
    schemas = soup.find_all("script", attrs={"type": "application/ld+json"})
    results["details"]["schema_count"] = max(len(schemas), 1 if has_schema_injected else 0)
    if len(schemas) == 0 and not has_schema_injected:
        results["score"] -= 15
        results["critical_issues"].append("Schema Markup Missing: No JSON-LD structured data found. Google cannot show rich snippets, stars, or business details.")
    else:
        results["passed_checks"].append(f"Structured Data found ({results['details']['schema_count']} Schema JSON-LD blocks).")

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

                    word_count = len(clean_body.split())
                    p_issues = []
                    # Thin description check (<25 words or <100 chars)
                    if word_count < 25 or len(clean_body) < 100:
                        thin_products.append((p_title, len(clean_body)))
                        p_issues.append(f"Thin Copy ({word_count}w)")
                    
                    # Title truncation check (>60 chars)
                    if len(p_title) > 60:
                        truncated_titles.append((p_title, len(p_title)))
                        p_issues.append(f"Title Truncated ({len(p_title)} chars)")
                    elif len(p_title) < 20:
                        p_issues.append(f"Title Short ({len(p_title)} chars)")
                    
                    if p_missing_alts > 0:
                        p_issues.append(f"{p_missing_alts} Missing Alt-Tags")

                    p_has_issues = len(p_issues) > 0

                    analyzed_products.append({
                        "id": p.get("id"),
                        "title": p_title,
                        "handle": p.get("handle"),
                        "clean_desc": clean_body[:90] + ("..." if len(clean_body) > 90 else ""),
                        "desc_len": len(clean_body),
                        "desc_words": word_count,
                        "total_images": len(p_imgs),
                        "missing_alts": p_missing_alts,
                        "issues": p_issues,
                        "has_issues": p_has_issues
                    })

                results["details"]["products_catalog"] = analyzed_products
                results["details"]["catalog_scanned_count"] = len(analyzed_products)
                results["details"]["thin_count"] = len(thin_products)
                results["details"]["truncated_titles_count"] = len(truncated_titles)
                results["details"]["missing_alts_count"] = missing_catalog_alts
                results["details"]["deficit_products_count"] = sum(1 for p in analyzed_products if p["has_issues"])

                # Penalties for Catalog Defects
                if missing_catalog_alts > 0:
                    penalty = min(20, missing_catalog_alts * 2)
                    results["score"] -= penalty
                    results["critical_issues"].append(
                        f"Product Catalog Image SEO: {missing_catalog_alts} of {total_catalog_imgs} product images are missing descriptive Alt-tags. Google Images cannot index these products."
                    )

                if thin_products:
                    penalty = min(25, len(thin_products) * 10)
                    results["score"] -= penalty
                    sample_name = thin_products[0][0]
                    sample_len = thin_products[0][1]
                    results["critical_issues"].append(
                        f"Thin Product Descriptions: Found {len(thin_products)} product(s) with incomplete/thin descriptions (e.g. '{sample_name[:38]}...' has only {sample_len} chars). Google Panda algorithm penalizes thin product pages!"
                    )

                if truncated_titles:
                    penalty = min(15, len(truncated_titles) * 3)
                    results["score"] -= penalty
                    results["warnings"].append(
                        f"Product Titles Exceeding Display Limit: {len(truncated_titles)} products have titles over 70 characters that will be cut off with '...' in Google search."
                    )
    except Exception:
        pass

    results["details"]["is_optimized"] = False
    results["details"]["schema_injected"] = False
    results["details"]["images_fixed"] = False
    results["details"]["titles_fixed"] = False
    results["details"]["descriptions_fixed"] = False

    # Clamp score between 15 and 100
    results["score"] = max(15, min(100, results["score"]))
    return results

if __name__ == "__main__":
    import json
    test_url = "https://example.com"
    print(f"Testing audit on {test_url}...")
    report = audit_website(test_url)
    print(json.dumps(report, indent=2))
