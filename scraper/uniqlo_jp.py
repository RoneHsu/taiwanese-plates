"""
Scraper for Uniqlo Japan
API: GET https://www.uniqlo.com/jp/api/commerce/v5/ja/products
"""

import httpx
import asyncio
from typing import AsyncGenerator

BASE_URL = "https://www.uniqlo.com/jp/api/commerce/v5/ja/products"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "ja-JP,ja;q=0.9",
}

# Gender path IDs: 1072=Men, 1073=Women, 1074=Kids, 1076=Baby
GENDER_PATHS = {
    "men": "1072",
    "women": "1073",
    "kids": "1074",
    "baby": "1076",
}

PAGE_SIZE = 36


async def fetch_jp_product_by_id(product_id: str) -> dict | None:
    """Query JP API for a specific product ID. Returns normalized dict or None if not found."""
    params = {
        "goods": product_id,
        "httpFailure": "true",
    }
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=30) as client:
            resp = await client.get(BASE_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("result", {}).get("items", [])
            if items:
                return normalize_jp(items[0], "unknown")
    except Exception:
        pass
    return None


async def fetch_products_jp(path: str, limit: int = PAGE_SIZE, offset: int = 0) -> dict:
    params = {
        "path": path,
        "limit": limit,
        "offset": offset,
        "httpFailure": "true",
    }
    async with httpx.AsyncClient(headers=HEADERS, timeout=30) as client:
        resp = await client.get(BASE_URL, params=params)
        resp.raise_for_status()
        return resp.json()


async def scrape_all_jp() -> AsyncGenerator[dict, None]:
    """Yields normalized product dicts from Uniqlo JP across all gender categories."""
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
                resp = await client.get(BASE_URL, params=params)
                resp.raise_for_status()
                data = resp.json()

                result = data.get("result", {})
                pagination = result.get("pagination", {})
                total = pagination.get("total", 0)
                items = result.get("items", [])

                if not items:
                    break

                for item in items:
                    yield normalize_jp(item, gender)

                offset += PAGE_SIZE
                print(f"[JP] {gender}: {min(offset, total)}/{total}")
                await asyncio.sleep(0.5)  # Be polite


def normalize_jp(item: dict, gender: str) -> dict:
    """Map JP API response to a common schema."""
    prices = item.get("prices") or {}
    base = prices.get("base") or {}
    promo = prices.get("promo") or {}

    # l1Id is the numeric global product ID (used for JP/TW matching)
    product_id = str(item.get("l1Id", ""))

    # Get the first image — structure: images.main.{colorCode}.image
    images_main = item.get("images", {}).get("main", {})
    first_color = next(iter(images_main.values()), None)
    image_url = first_color.get("image") if first_color else None

    return {
        "uniqlo_product_id": product_id,
        "name_jp": item.get("name", ""),
        "category": gender,
        "image_url": image_url,
        "region": "JP",
        "price": promo.get("value") or base.get("value"),
        "currency": "JPY",
    }
