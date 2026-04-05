"""
Step 3 — FastAPI backend
Endpoints:
  GET /api/v1/products          - product list with price comparison
  GET /api/v1/products/{id}     - single product detail
  GET /api/v1/exchange-rate     - latest JPY→TWD rate
"""

import os
import ssl
import asyncpg
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

app = FastAPI(title="Compare Money API", version="1.0.0")

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*"],
)


# --- DB pool ---

@app.on_event("startup")
async def startup():
    use_ssl = os.getenv("DATABASE_SSL", "false").lower() == "true"
    ssl_ctx = None
    if use_ssl:
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
    app.state.pool = await asyncpg.create_pool(DATABASE_URL, ssl=ssl_ctx, min_size=1, max_size=10, statement_cache_size=0)


@app.on_event("shutdown")
async def shutdown():
    await app.state.pool.close()


@app.get("/health")
async def health():
    return {"status": "ok"}


# --- Helpers ---

async def get_latest_rate(conn) -> float:
    row = await conn.fetchrow("""
        SELECT rate FROM exchange_rates
        ORDER BY fetched_at DESC LIMIT 1
    """)
    return float(row["rate"]) if row else 0.21


def parse_colors(colors_str: str | None) -> list[dict] | None:
    """Parse '01:OFF WHITE/09:BLACK' → [{'code':'01','name':'OFF WHITE'}, ...]
    Also handles legacy GU TW format '357680:/ 09 BLACK' where the product ID
    bled into the code field — extracts the actual color code after '/'.
    """
    if not colors_str:
        return None
    result = []
    seen = set()
    for pair in colors_str.split("/"):
        if ":" not in pair:
            continue
        code, name = pair.split(":", 1)
        code = code.strip()
        name = name.strip()
        # Legacy GU TW: code contains product_id, name starts with "/ NN COLOR"
        if name.startswith("/ ") and " " in name[2:]:
            rest = name[2:].strip()  # "09 BLACK"
            parts = rest.split(" ", 1)
            if len(parts) == 2:
                code = parts[0]
                name = parts[1]
        if code and name and code not in seen:
            seen.add(code)
            result.append({"code": code, "name": name})
    return result if result else None


def build_comparison(jp_price: int, tw_price: int, rate: float) -> dict:
    jp_in_twd = round(jp_price * rate)
    diff = tw_price - jp_in_twd
    diff_pct = round((diff / jp_in_twd) * 100) if jp_in_twd else 0

    if diff > 0:
        suggestion = f"台灣貴 NT${diff}（{diff_pct}%），考慮從日本購買"
    elif diff < 0:
        suggestion = f"日本貴 NT${abs(diff)}（{abs(diff_pct)}%），台灣購買較划算"
    else:
        suggestion = "兩地價格相同"

    return {
        "jp_price_jpy": jp_price,
        "jp_price_twd": jp_in_twd,
        "tw_price_twd": tw_price,
        "diff_twd": diff,
        "diff_pct": diff_pct,
        "suggestion": suggestion,
    }


def build_product_urls(brand: str, product_id: str) -> dict:
    if brand == "gu":
        return {
            "jp_url": f"https://www.gu-global.com/jp/ja/products/{product_id}/",
            "tw_url": f"https://www.gu-global.com/tw/zh_TW/products/{product_id}/",
        }
    return {
        "jp_url": f"https://www.uniqlo.com/jp/ja/products/{product_id}/",
        "tw_url": f"https://www.uniqlo.com/tw/product-detail.html?productCode={product_id}",
    }


# --- Endpoints ---

@app.get("/api/v1/exchange-rate")
async def get_exchange_rate():
    async with app.state.pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT rate, fetched_at FROM exchange_rates
            ORDER BY fetched_at DESC LIMIT 1
        """)
    if not row:
        raise HTTPException(status_code=404, detail="No exchange rate available")
    return {
        "from": "JPY",
        "to": "TWD",
        "rate": float(row["rate"]),
        "fetched_at": row["fetched_at"].isoformat(),
    }


@app.get("/api/v1/products")
async def list_products(
    q: str = Query(None, description="Search by name"),
    category: str = Query(None, description="Filter by category"),
    brand: str = Query(None, description="Filter by brand: uniqlo | gu"),
    sort: str = Query("diff_desc", description="Sort: diff_desc | diff_asc | price_jp | price_tw"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    async with app.state.pool.acquire() as conn:
        rate = await get_latest_rate(conn)

        # Build WHERE clause
        conditions = []
        params = []

        if q:
            params.append(f"%{q}%")
            conditions.append(f"(p.name_jp ILIKE ${len(params)} OR p.name_tw ILIKE ${len(params)})")

        if category:
            params.append(category)
            conditions.append(f"p.category = ${len(params)}")

        if brand:
            params.append(brand)
            conditions.append(f"p.brand = ${len(params)}")

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        # Sort
        order_map = {
            "diff_desc": "(tw.price - ROUND(jp.price * $RATE)) DESC",
            "diff_asc":  "(tw.price - ROUND(jp.price * $RATE)) ASC",
            "price_jp":  "jp.price ASC",
            "price_tw":  "tw.price ASC",
        }
        order_sql = order_map.get(sort, order_map["diff_desc"])
        order_sql = order_sql.replace("$RATE", str(rate))

        rows = await conn.fetch(f"""
            SELECT
                p.id,
                p.brand,
                p.uniqlo_product_id,
                p.name_jp,
                p.name_tw,
                p.category,
                p.image_url,
                p.colors,
                p.sizes,
                jp.price AS price_jpy,
                tw.price AS price_twd
            FROM products p
            JOIN LATERAL (
                SELECT price FROM prices
                WHERE product_id = p.id AND region = 'JP'
                ORDER BY scraped_at DESC LIMIT 1
            ) jp ON true
            JOIN LATERAL (
                SELECT price FROM prices
                WHERE product_id = p.id AND region = 'TW'
                ORDER BY scraped_at DESC LIMIT 1
            ) tw ON true
            {where}
        """, *params)

        total = len(rows)

        def sort_key(r):
            jp_in_twd = r["price_jpy"] * rate
            diff = r["price_twd"] - jp_in_twd
            if sort == "diff_asc":
                return diff
            elif sort == "price_jp":
                return r["price_jpy"]
            elif sort == "price_tw":
                return r["price_twd"]
            return -diff

        rows = sorted(rows, key=sort_key)
        rows = rows[offset: offset + limit]

    products = []
    for r in rows:
        comparison = build_comparison(r["price_jpy"], r["price_twd"], rate)
        urls = build_product_urls(r["brand"], r["uniqlo_product_id"])
        products.append({
            "id": r["id"],
            "brand": r["brand"],
            "uniqlo_product_id": r["uniqlo_product_id"],
            "name_jp": r["name_jp"],
            "name_tw": r["name_tw"],
            "category": r["category"],
            "image_url": r["image_url"],
            "colors": parse_colors(r["colors"]),
            "sizes": r["sizes"],
            **comparison,
            **urls,
        })

    return {
        "data": products,
        "meta": {
            "total": total,
            "limit": limit,
            "offset": offset,
            "exchange_rate": rate,
        },
    }


@app.get("/api/v1/products/{product_id}")
async def get_product(product_id: int):
    async with app.state.pool.acquire() as conn:
        rate = await get_latest_rate(conn)

        row = await conn.fetchrow("""
            SELECT
                p.id,
                p.brand,
                p.uniqlo_product_id,
                p.name_jp,
                p.name_tw,
                p.category,
                p.image_url,
                p.colors,
                p.sizes,
                jp.price AS price_jpy,
                tw.price AS price_twd
            FROM products p
            JOIN LATERAL (
                SELECT price FROM prices
                WHERE product_id = p.id AND region = 'JP'
                ORDER BY scraped_at DESC LIMIT 1
            ) jp ON true
            JOIN LATERAL (
                SELECT price FROM prices
                WHERE product_id = p.id AND region = 'TW'
                ORDER BY scraped_at DESC LIMIT 1
            ) tw ON true
            WHERE p.id = $1
        """, product_id)

    if not row:
        raise HTTPException(status_code=404, detail="Product not found")

    comparison = build_comparison(row["price_jpy"], row["price_twd"], rate)
    urls = build_product_urls(row["brand"], row["uniqlo_product_id"])
    return {
        "id": row["id"],
        "brand": row["brand"],
        "uniqlo_product_id": row["uniqlo_product_id"],
        "name_jp": row["name_jp"],
        "name_tw": row["name_tw"],
        "category": row["category"],
        "image_url": row["image_url"],
        "colors": parse_colors(row["colors"]),
        "sizes": row["sizes"],
        **comparison,
        **urls,
    }
