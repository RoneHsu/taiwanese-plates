"""
Scraper for GU Japan
API: GET https://www.gu-global.com/jp/api/commerce/v5/ja/products
"""

import httpx
import asyncio
from typing import AsyncGenerator

BASE_URL = "https://www.gu-global.com/jp/api/commerce/v5/ja/products"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "ja-JP,ja;q=0.9",
}

# GU Japan gender category path IDs (same as Uniqlo JP uses 'path' param)
GENDER_PATHS = {
    "women": "2256",
    "men": "2257",
    "kids": "2258",
}

PAGE_SIZE = 36


async def scrape_all_gu_jp() -> AsyncGenerator[dict, None]:
    """Yields normalized GU JP product dicts across all gender categories."""
    async with httpx.AsyncClient(headers=HEADERS, timeout=30) as client:
        for gender, path in GENDER_PATHS.items():
            offset = 0
            total = None

            while total is None or offset < total:
                params = {
                    "path": path,
                    "limit": PAGE_SIZE,
                    "offset": offset,
                    "httpFailure": "true",
                }
                try:
                    resp = await client.get(BASE_URL, params=params)
                    resp.raise_for_status()
                    data = resp.json()
                except httpx.HTTPError as e:
                    print(f"[GU JP] Error fetching {gender} offset={offset}: {e}")
                    break

                result = data.get("result", {})
                pagination = result.get("pagination", {})
                total = pagination.get("total", 0)
                items = result.get("items", [])

                if not items:
                    break

                for item in items:
                    yield normalize_gu_jp(item, gender)

                offset += PAGE_SIZE
                print(f"[GU JP] {gender}: {min(offset, total)}/{total}")
                await asyncio.sleep(0.5)


async def fetch_gu_jp_product_by_id(product_id: str) -> dict | None:
    """Query GU JP API for a specific product ID."""
    params = {"goods": product_id, "httpFailure": "true"}
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=30) as client:
            resp = await client.get(BASE_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("result", {}).get("items", [])
            if items:
                return normalize_gu_jp(items[0], "unknown")
    except Exception:
        pass
    return None


def normalize_gu_jp(item: dict, gender: str) -> dict:
    """Map GU JP API response to common schema."""
    prices = item.get("prices") or {}
    base = prices.get("base") or {}
    promo = prices.get("promo") or {}

    product_id = str(item.get("l1Id", ""))

    # Get image from API response; fall back to constructing CDN URL
    images_main = item.get("images", {}).get("main", {})
    first_color_key = next(iter(images_main), None)
    first_color_data = images_main.get(first_color_key) if first_color_key else None

    if first_color_data and first_color_data.get("image"):
        image_url = first_color_data["image"]
    elif first_color_key and product_id:
        image_url = (
            f"https://image.uniqlo.com/GU/ST3/AsianCommon/imagesgoods"
            f"/{product_id}/item/goods_{first_color_key}_{product_id}_3x4.jpg"
        )
    else:
        image_url = None

    return {
        "brand": "gu",
        "uniqlo_product_id": product_id,
        "name_jp": item.get("name", ""),
        "category": gender,
        "image_url": image_url,
        "region": "JP",
        "price": promo.get("value") or base.get("value"),
        "currency": "JPY",
    }
