"""
Scraper for Uniqlo Taiwan
API: POST https://d.uniqlo.com/tw/p/search/products/by-category
"""

import httpx
import asyncio
from typing import AsyncGenerator

BASE_URL = "https://d.uniqlo.com/tw/p/search/products/by-category"
CATEGORY_URL = "https://www.uniqlo.com/tw/data/zh_TW/shop_classification_PC.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "zh-TW,zh;q=0.9",
    "Content-Type": "application/json",
}

PAGE_SIZE = 36


CATEGORY_CODES = [
    # Men - Outer
    "all_men-outer",
    # Men - Tops
    "all_men-tops-t-shirts",
    "all_men-tops-polo",
    "all_men-tops-casual-shirts-long",
    "all_men-tops-dress-shirts",
    "all_men-tops-sweat-collection",
    "all_men-knit-lineup",
    # Men - Bottoms
    "all_men-bottoms-jeans",
    "all_men-bottoms-easy-pants",
    "all_men-bottoms-short-pants",
    "all_men-bottoms-chino",
    "all_men-bottoms-cargopants",
    # Men - Innerwear
    "all_men-inner-wear-heattech",
    "all_men-inner-wear-airism",
    "all_men-inner-wear-trunks-and-brief",
    "all_men-inner-wear-socks",
    # Women - Outer
    "all_women-outer",
    # Women - Tops
    "all_women-tops-t-shirts",
    "all_women-tops-shirts-and-blouses",
    "all_women-tops-polo",
    "all_women-tops-sweat",
    "all_women-knit-lineup",
    # Women - Bottoms
    "all_women-bottoms-jeans",
    "all_women-bottoms-easy-pants",
    "all_women-bottoms-short-pants",
    "all_women-bottoms-widepants",
    "all_women-bottoms-leggings",
    # Women - Dresses & Skirts
    "all_women-dresses-and-skirts-dresses",
    "all_women-dresses-and-skirts-skirts",
    # Women - Innerwear
    "all_women-inner-wear-heattech",
    "all_women-inner-wear-airism",
    "all_women-inner-wear-socks",
    # Kids - Tops & Bottoms
    "all_kids-tops",
    "all_kids-bottoms",
    "all_kids-inner-wear",
    # Baby
    "all_baby-toddler",
    "all_baby-newborn-lineup",
]


async def fetch_categories_tw() -> list[str]:
    return CATEGORY_CODES


async def fetch_products_tw(category_code: str, page: int = 1) -> dict:
    payload = {
        "categoryCode": category_code,
        "pageInfo": {"page": page, "pageSize": PAGE_SIZE},
    }
    async with httpx.AsyncClient(headers=HEADERS, timeout=30) as client:
        resp = await client.post(BASE_URL, json=payload)
        resp.raise_for_status()
        return resp.json()


async def scrape_all_tw() -> AsyncGenerator[dict, None]:
    """Yields normalized product dicts from Uniqlo TW across all categories."""
    categories = await fetch_categories_tw()
    print(f"[TW] Found {len(categories)} categories")

    async with httpx.AsyncClient(headers=HEADERS, timeout=30) as client:
        for category_code in categories:
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
                    print(f"[TW] Error fetching {category_code} page {page}: {e}")
                    break

                if not data.get("success"):
                    break

                resp_data = data.get("resp", [{}])[0]
                total = resp_data.get("productSum", 0)
                products = resp_data.get("productList", [])

                if not products:
                    break

                for item in products:
                    yield normalize_tw(item, category_code)

                fetched = (page - 1) * PAGE_SIZE + len(products)
                print(f"[TW] {category_code}: {fetched}/{total}")
                page += 1
                await asyncio.sleep(0.5)


def _simplify_category(category_code: str) -> str:
    """Map TW category code to simple gender category."""
    if category_code.startswith("all_baby"):
        return "baby"
    if category_code.startswith("all_kids"):
        return "kids"
    if category_code.startswith("all_women"):
        return "women"
    if category_code.startswith("all_men"):
        return "men"
    return category_code


def _parse_colors(style_text) -> str | None:
    """從 styleText 解析顏色，例：['01 OFF WHITE', '09 BLACK'] → '01:OFF WHITE/09:BLACK'"""
    if not style_text:
        return None
    try:
        # API 可能回傳 list 或 list 的字串表示
        if isinstance(style_text, str):
            import ast
            style_text = ast.literal_eval(style_text)
        # 每項格式為 "01 OFF WHITE"，保留色碼以便前端構建圖片 URL
        pairs = []
        for s in style_text:
            if " " in s:
                code, name = s.split(" ", 1)
                name = name.strip()
                if name:
                    pairs.append(f"{code}:{name}")
        return "/".join(pairs) if pairs else None
    except Exception:
        return None


def normalize_tw(item: dict, category: str) -> dict:
    """Map TW API response to a common schema."""
    # masterSpuCode is the numeric global product ID (matches JP's l1Id)
    product_id = str(item.get("masterSpuCode", ""))

    # Use sale price if available, else regular price
    price = item.get("minVaryPrice") or item.get("minPrice") or item.get("originPrice")

    # mainPic is a relative path, prepend CDN base
    main_pic = item.get("mainPic", "")
    image_url = f"https://www.uniqlo.com{main_pic}" if main_pic else None

    # 顏色：從 styleText 解析
    colors = _parse_colors(item.get("styleText", ""))

    # 尺寸：用 minSize ~ maxSize 表示範圍
    min_size = item.get("minSize", "")
    max_size = item.get("maxSize", "")
    if min_size and max_size and min_size != max_size:
        sizes = f"{min_size} ~ {max_size}"
    elif min_size:
        sizes = min_size
    else:
        sizes = None

    name_tw = item.get("productName", "")
    simplified = _simplify_category(category)
    # 依名稱前綴覆寫分類，避免 TW API 把商品放錯分類
    if "\u7537\u5973\u9069\u7a7f" in name_tw:          # 含「男女適穿」→ unisex
        simplified = "unisex"
    elif name_tw.startswith("\u5973\u88dd"):            # 純女裝 → women
        simplified = "women"
    elif name_tw.startswith("\u7537\u88dd"):            # 純男裝 → men
        simplified = "men"

    return {
        "uniqlo_product_id": product_id,
        "name_tw": name_tw,
        "category": simplified,
        "image_url": image_url,
        "colors": colors,
        "sizes": sizes,
        "region": "TW",
        "price": price,
        "currency": "TWD",
    }
