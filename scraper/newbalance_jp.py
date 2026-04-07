"""
Scraper for New Balance Japan
Site: https://shop.newbalance.jp
Method: HTML scraping via curl_cffi (Akamai bypass) + Tealium product tile data
"""

import asyncio
import html as html_module
import json
import re
from typing import AsyncGenerator

from curl_cffi import requests as cffi_requests

BASE_URL = "https://shop.newbalance.jp/search"
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
    "Accept-Language": "ja-JP,ja;q=0.9",
    "Referer": "https://shop.newbalance.jp/",
}

# Search terms that cover all NB JP product categories
SEARCH_QUERIES = ["shoes", "clothing", "accessories"]


def _normalize_product_id(raw_id: str) -> str:
    """Strip color/variant/region suffixes from SFCC product ID for cross-region matching.

    BB100V1-46995          → BB100V1
    CT500V1-46313-PMG-APAC → CT500V1
    CM996V2-37921          → CM996V2
    U574V2_LI-FTW          → U574V2
    U740V2_LI-FTW          → U740V2
    AC0207F                → AC0207F  (accessories, unchanged)
    """
    # Strip APAC/region locale suffixes (e.g. _LI-FTW, _KP-FTW)
    raw_id = re.sub(r"_[A-Z]{2}-[A-Z]+.*$", "", raw_id)
    # Strip numeric color code suffix (e.g. -46995, -37921)
    raw_id = re.sub(r"-\d{4,}.*$", "", raw_id)
    return raw_id


def _classify_gender(gender_raw: str) -> str:
    """Map NB JP gender field value to standard category."""
    g = gender_raw.lower()
    if "men's" in g or "male" in g or "mens" in g or g == "men":
        return "men"
    if "women" in g or "ladies" in g or "female" in g or g == "women":
        return "women"
    if "kid" in g or "boy" in g or "girl" in g or "child" in g or "junior" in g:
        return "kids"
    if "unisex" in g or g == "neutral" or g == "gender neutral":
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

    # Sales price: <span content="PRICE"> (integer, no decimals for JPY)
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

    return {
        "brand": "newbalance",
        "uniqlo_product_id": master_id,
        "name_jp": product_name,
        "category": category,
        "image_url": image_url,
        "region": "JP",
        "price": price,
        "currency": "JPY",
    }


def _extract_tiles(content: str) -> list[dict]:
    """Extract all product tiles from a search result page."""
    # Each tile starts with class="pgptiles and ends at the next tile or end sentinel
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


async def scrape_all_newbalance_jp() -> AsyncGenerator[dict, None]:
    """
    Yields normalized New Balance JP product dicts.

    Uses curl_cffi with chrome110 impersonation to bypass Akamai Bot Manager.
    Paginates through each search query using start/sz parameters.
    """
    seen_global: set[str] = set()

    for query in SEARCH_QUERIES:
        start = 0
        page_num = 0

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
                print(f"[NB JP] Error fetching q={query} start={start}: {e}")
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

            page_num += 1
            has_more = bool(re.search(r'id="btn-loadMore"', content))
            print(
                f"[NB JP] q={query} start={start}: "
                f"{len(products)} tiles, {new_count} new, total={len(seen_global)}"
            )

            if not has_more or len(products) < PAGE_SIZE:
                break

            start += PAGE_SIZE
            await asyncio.sleep(0.5)

        await asyncio.sleep(0.5)
