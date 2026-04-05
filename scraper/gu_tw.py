"""
Scraper for GU Taiwan
API: POST https://d.gu-global.com/tw/p/search/products/by-category
     (same structure as Uniqlo TW)
"""

import httpx
import asyncio
import ast
from typing import AsyncGenerator

BASE_URL = "https://d.gu-global.com/tw/p/search/products/by-category"
IMAGE_CDN = "https://www.gu-global.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "zh-TW,zh;q=0.9",
    "Content-Type": "application/json",
}

# GU TW category codes (confirmed working)
CATEGORY_CODES = [
    ("women_all", "women"),
    ("men_all", "men"),
    ("kids_all", "kids"),
]

PAGE_SIZE = 36


async def scrape_all_gu_tw() -> AsyncGenerator[dict, None]:
    """Yields normalized GU TW product dicts."""
    async with httpx.AsyncClient(headers=HEADERS, timeout=30) as client:
        for category_code, gender in CATEGORY_CODES:
            page = 1
            total = None

            while total is None or (page - 1) * PAGE_SIZE < total:
                payload = {
                    "categoryCode": category_code,
                    "pageInfo": {"page": page, "pageSize": PAGE_SIZE},
                }
                try:
                    resp = await client.post(BASE_URL, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                except httpx.HTTPError as e:
                    print(f"[GU TW] Error fetching {category_code} page {page}: {e}")
                    break

                if not data.get("success"):
                    break

                resp_data = data.get("resp", [{}])[0]
                total = resp_data.get("productSum", 0)
                products = resp_data.get("productList", [])

                if not products:
                    break

                for item in products:
                    yield normalize_gu_tw(item, gender)

                fetched = (page - 1) * PAGE_SIZE + len(products)
                print(f"[GU TW] {category_code}: {fetched}/{total}")
                page += 1
                await asyncio.sleep(0.5)


def normalize_gu_tw(item: dict, gender: str) -> dict:
    """Map GU TW API response to common schema."""
    product_id = str(item.get("masterSpuCode", ""))
    price = item.get("minVaryPrice") or item.get("minPrice") or item.get("originPrice")

    main_pic = item.get("mainPic", "")
    image_url = f"{IMAGE_CDN}{main_pic}" if main_pic else None

    colors = _parse_colors(item.get("styleText", ""))

    min_size = item.get("minSize", "")
    max_size = item.get("maxSize", "")
    if min_size and max_size and min_size != max_size:
        sizes = f"{min_size} ~ {max_size}"
    elif min_size:
        sizes = min_size
    else:
        sizes = None

    name_tw = item.get("productName", "")
    category = _classify_gender(name_tw, gender)

    return {
        "brand": "gu",
        "uniqlo_product_id": product_id,
        "name_tw": name_tw,
        "category": category,
        "image_url": image_url,
        "colors": colors,
        "sizes": sizes,
        "region": "TW",
        "price": price,
        "currency": "TWD",
    }


def _classify_gender(name: str, default: str) -> str:
    """Infer gender category from product name."""
    if "男女" in name or "unisex" in name.lower():
        return "unisex"
    if name.startswith("女裝"):
        return "women"
    if name.startswith("男裝"):
        return "men"
    return default


def _parse_colors(style_text) -> str | None:
    """Parse styleText list → '01:OFF WHITE/09:BLACK'

    GU TW styleText may be in two formats:
      - '09 BLACK'           (standard: code=09, name=BLACK)
      - '357680 / 09 BLACK'  (product_id / code name — extract code+name after '/')
    """
    if not style_text:
        return None
    try:
        if isinstance(style_text, str):
            style_text = ast.literal_eval(style_text)
        pairs = []
        seen_codes = set()
        for s in style_text:
            s = s.strip()
            # Format: "357680 / 09 BLACK" — take everything after '/'
            if " / " in s:
                s = s.split(" / ", 1)[1].strip()
            # Now expect "09 BLACK"
            if " " in s:
                code, name = s.split(" ", 1)
                name = name.strip()
                if name and code not in seen_codes:
                    seen_codes.add(code)
                    pairs.append(f"{code}:{name}")
        return "/".join(pairs) if pairs else None
    except Exception:
        return None
