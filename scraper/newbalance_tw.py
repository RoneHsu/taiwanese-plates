"""
Scraper for New Balance Taiwan
Site: https://www.newbalance.com.tw
Method: HTML scraping via curl_cffi (Akamai bypass) + Tealium product tile data
"""

import asyncio
import html as html_module
import json
import re
from typing import AsyncGenerator

from curl_cffi import requests as cffi_requests

BASE_URL = "https://www.newbalance.com.tw/search"
PAGE_SIZE = 60

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/110.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "zh-TW,zh;q=0.9",
    "Referer": "https://www.newbalance.com.tw/",
}

# Search terms that cover all NB TW product categories
SEARCH_QUERIES = ["shoes", "clothing", "accessories"]


def _normalize_product_id(raw_id: str) -> str:
    """Strip color/variant/region suffixes from SFCC product ID for cross-region matching.

    BB100V1-46995          → BB100V1
    CT500V1-46313-PMG-APAC → CT500V1
    CM996V2-37921          → CM996V2
    U574V2_LI-FTW          → U574V2
    U740V2_LI-FTW          → U740V2
    AMJ53638               → AMJ53638  (apparel, unchanged)
    """
    # Strip APAC/region locale suffixes (e.g. _LI-FTW, _KP-FTW)
    raw_id = re.sub(r"_[A-Z]{2}-[A-Z]+.*$", "", raw_id)
    # Strip numeric color code suffix (e.g. -46995, -37921)
    raw_id = re.sub(r"-\d{4,}.*$", "", raw_id)
    return raw_id


def _classify_gender(gender_raw: str) -> str:
    """Map NB TW gender field value to standard category."""
    g = gender_raw.lower()
    # Chinese gender values: 男款/男性, 女款/女性, 中性, 男童, 女童
    if "男款" in gender_raw or "男性" in gender_raw or g == "men" or "mens" in g or "male" in g:
        return "men"
    if "女款" in gender_raw or "女性" in gender_raw or g == "women" or "women" in g or "ladies" in g:
        return "women"
    if "童" in gender_raw or "kid" in g or "boy" in g or "girl" in g or "junior" in g or "child" in g:
        return "kids"
    if "中性" in gender_raw or "unisex" in g or "neutral" in g or "gender neutral" in g:
        return "unisex"
    return "unisex"


def _parse_tile(tile_html: str) -> dict | None:
    """
    Parse a single SFCC product tile block.

    Returns a normalized product dict or None if required fields are missing.
    """
    # Tealium data attribute contains rich product metadata as HTML-escaped JSON
    tealium_match = re.search(
        r'data-tealium-product-tile-data="(\{[^"]+\})"', tile_html
    )
    if not tealium_match:
        return None

    try:
        tealium = json.loads(html_module.unescape(tealium_match.group(1)))
    except (json.JSONDecodeError, ValueError):
        return None

    master_id = tealium.get("masterProductId") or tealium.get("productId")
    if not master_id:
        return None
    master_id = _normalize_product_id(master_id)

    product_name = tealium.get("productName", "")
    gender_raw = tealium.get("gender", "")
    category = _classify_gender(gender_raw)
    color = tealium.get("color") or None

    # Sales price: <span content="PRICE"> (integer, TWD has no decimals in display)
    price_match = re.search(r'<span content="(\d+)"', tile_html)
    if not price_match:
        return None
    price = int(price_match.group(1))

    # Image: Scene7 CDN URL (strip query string)
    image_url = None
    img_match = re.search(r'src="(https://nb\.scene7\.com[^"?]+)', tile_html)
    if not img_match:
        img_match = re.search(r'srcset="(https://nb\.scene7\.com[^"? ]+)', tile_html)
    if img_match:
        image_url = img_match.group(1).rstrip("/")

    # Sizes: not available at tile level; NB TW does not expose sizes in search results
    sizes = None

    return {
        "brand": "newbalance",
        "uniqlo_product_id": master_id,
        "name_tw": product_name,
        "category": category,
        "image_url": image_url,
        "colors": color,
        "sizes": sizes,
        "region": "TW",
        "price": price,
        "currency": "TWD",
    }


def _extract_tiles(content: str) -> list[dict]:
    """Extract all product tiles from a search result page."""
    tile_chunks = re.findall(
        r'class="pgptiles[^"]*"[^>]*>(.*?)(?=class="pgptiles|<div class="no-results|'
        r'<section id="contact)',
        content,
        re.DOTALL,
    )
    products = []
    seen_ids: set[str] = set()
    for chunk in tile_chunks:
        product = _parse_tile(chunk)
        if product and product["uniqlo_product_id"] not in seen_ids:
            seen_ids.add(product["uniqlo_product_id"])
            products.append(product)
    return products


async def scrape_all_newbalance_tw() -> AsyncGenerator[dict, None]:
    """
    Yields normalized New Balance TW product dicts.

    Uses curl_cffi with chrome110 impersonation to bypass Akamai Bot Manager.
    Paginates through each search query using start/sz parameters.
    """
    seen_global: set[str] = set()

    for query in SEARCH_QUERIES:
        start = 0

        while True:
            params = f"q={query}&start={start}&sz={PAGE_SIZE}"
            url = f"{BASE_URL}?{params}"

            try:
                resp = cffi_requests.get(
                    url,
                    impersonate="chrome110",
                    timeout=30,
                    headers=HEADERS,
                )
                resp.raise_for_status()
            except Exception as e:
                print(f"[NB TW] Error fetching q={query} start={start}: {e}")
                break

            content = resp.content.decode("utf-8", errors="replace")
            products = _extract_tiles(content)

            if not products:
                break

            new_count = 0
            for product in products:
                pid = product["uniqlo_product_id"]
                if pid not in seen_global:
                    seen_global.add(pid)
                    yield product
                    new_count += 1

            has_more = bool(re.search(r'id="btn-loadMore"', content))
            print(
                f"[NB TW] q={query} start={start}: "
                f"{len(products)} tiles, {new_count} new, total={len(seen_global)}"
            )

            if not has_more or len(products) < PAGE_SIZE:
                break

            start += PAGE_SIZE
            await asyncio.sleep(0.5)

        await asyncio.sleep(0.5)
