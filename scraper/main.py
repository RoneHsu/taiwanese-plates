"""
Main scraper entry point.
Scrapes Uniqlo JP, Uniqlo TW, GU JP, GU TW, New Balance JP, and New Balance TW;
stores results in PostgreSQL.

Usage:
    python main.py                # scrape all brands
    python main.py uniqlo         # scrape Uniqlo only
    python main.py gu             # scrape GU only
    python main.py newbalance     # scrape New Balance only
"""

import asyncio
import asyncpg
import os
import sys
from dotenv import load_dotenv

from db import init_db, get_connection
from uniqlo_jp import scrape_all_jp, fetch_jp_product_by_id
from uniqlo_tw import scrape_all_tw
from gu_jp import scrape_all_gu_jp
from gu_tw import scrape_all_gu_tw
from newbalance_jp import scrape_all_newbalance_jp
from newbalance_tw import scrape_all_newbalance_tw

load_dotenv()


async def upsert_product(conn: asyncpg.Connection, product: dict) -> int:
    """Insert or update product, return its DB id."""
    region = product["region"]
    brand = product.get("brand", "uniqlo")

    if region == "JP":
        row = await conn.fetchrow("""
            INSERT INTO products (brand, uniqlo_product_id, name_jp, category, image_url, colors)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (brand, uniqlo_product_id) DO UPDATE
                SET name_jp = EXCLUDED.name_jp,
                    image_url = COALESCE(EXCLUDED.image_url, products.image_url),
                    colors = COALESCE(EXCLUDED.colors, products.colors),
                    updated_at = NOW()
            RETURNING id
        """, brand, product["uniqlo_product_id"], product["name_jp"],
             product["category"], product["image_url"], product.get("colors"))
    else:
        row = await conn.fetchrow("""
            INSERT INTO products (brand, uniqlo_product_id, name_tw, category, image_url, colors, sizes)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (brand, uniqlo_product_id) DO UPDATE
                SET name_tw = EXCLUDED.name_tw,
                    category = EXCLUDED.category,
                    image_url = COALESCE(products.image_url, EXCLUDED.image_url),
                    colors = EXCLUDED.colors,
                    sizes = EXCLUDED.sizes,
                    updated_at = NOW()
            RETURNING id
        """, brand, product["uniqlo_product_id"], product["name_tw"],
             product["category"], product["image_url"],
             product.get("colors"), product.get("sizes"))

    return row["id"]


async def insert_price(conn: asyncpg.Connection, product_db_id: int, product: dict):
    """Insert a price record."""
    await conn.execute("""
        INSERT INTO prices (product_id, region, price, currency)
        VALUES ($1, $2, $3, $4)
    """, product_db_id, product["region"], product["price"], product["currency"])


async def scrape_uniqlo_jp(conn: asyncpg.Connection):
    print("\n=== Scraping Uniqlo Japan ===")
    count = 0
    async for product in scrape_all_jp():
        if not product["uniqlo_product_id"] or not product["price"]:
            continue
        product.setdefault("brand", "uniqlo")
        product_id = await upsert_product(conn, product)
        await insert_price(conn, product_id, product)
        count += 1
    print(f"[Uniqlo JP] Done. {count} products saved.")


async def scrape_uniqlo_tw(conn: asyncpg.Connection):
    print("\n=== Scraping Uniqlo Taiwan ===")
    count = 0
    async for product in scrape_all_tw():
        if not product["uniqlo_product_id"] or not product["price"]:
            continue
        product.setdefault("brand", "uniqlo")
        product_id = await upsert_product(conn, product)
        await insert_price(conn, product_id, product)
        count += 1
    print(f"[Uniqlo TW] Done. {count} products saved.")


async def scrape_gu_jp(conn: asyncpg.Connection):
    print("\n=== Scraping GU Japan ===")
    count = 0
    async for product in scrape_all_gu_jp():
        if not product["uniqlo_product_id"] or not product["price"]:
            continue
        product_id = await upsert_product(conn, product)
        await insert_price(conn, product_id, product)
        count += 1
    print(f"[GU JP] Done. {count} products saved.")


async def scrape_gu_tw(conn: asyncpg.Connection):
    print("\n=== Scraping GU Taiwan ===")
    count = 0
    async for product in scrape_all_gu_tw():
        if not product["uniqlo_product_id"] or not product["price"]:
            continue
        product_id = await upsert_product(conn, product)
        await insert_price(conn, product_id, product)
        count += 1
    print(f"[GU TW] Done. {count} products saved.")


async def scrape_newbalance_jp(conn: asyncpg.Connection):
    print("\n=== Scraping New Balance Japan ===")
    count = 0
    async for product in scrape_all_newbalance_jp():
        if not product["uniqlo_product_id"] or not product["price"]:
            continue
        product_id = await upsert_product(conn, product)
        await insert_price(conn, product_id, product)
        count += 1
    print(f"[NB JP] Done. {count} products saved.")


async def scrape_newbalance_tw(conn: asyncpg.Connection):
    print("\n=== Scraping New Balance Taiwan ===")
    count = 0
    async for product in scrape_all_newbalance_tw():
        if not product["uniqlo_product_id"] or not product["price"]:
            continue
        product_id = await upsert_product(conn, product)
        await insert_price(conn, product_id, product)
        count += 1
    print(f"[NB TW] Done. {count} products saved.")


async def lookup_missing_jp(conn: asyncpg.Connection):
    """For Uniqlo TW-only products, query JP API directly by product ID."""
    print("\n=== Looking up Uniqlo TW-only products in JP API ===")

    rows = await conn.fetch("""
        SELECT p.id, p.uniqlo_product_id
        FROM products p
        WHERE p.brand = 'uniqlo'
        AND EXISTS (
            SELECT 1 FROM prices WHERE product_id = p.id AND region = 'TW'
        )
        AND NOT EXISTS (
            SELECT 1 FROM prices WHERE product_id = p.id AND region = 'JP'
        )
    """)

    print(f"[JP lookup] {len(rows)} TW-only products to check")
    found = 0

    for row in rows:
        product_id = row["uniqlo_product_id"]
        jp_data = await fetch_jp_product_by_id(product_id)

        if jp_data and jp_data.get("price"):
            jp_data["brand"] = "uniqlo"
            await conn.execute("""
                UPDATE products SET name_jp = $1,
                    image_url = COALESCE(image_url, $2),
                    updated_at = NOW()
                WHERE id = $3
            """, jp_data["name_jp"], jp_data["image_url"], row["id"])

            await insert_price(conn, row["id"], jp_data)
            found += 1
            print(f"[JP lookup] Found JP match: {product_id}")

        await asyncio.sleep(0.3)

    print(f"[JP lookup] Done. {found}/{len(rows)} products found in JP.")


async def main():
    target = sys.argv[1].lower() if len(sys.argv) > 1 else "all"

    print("Initializing database...")
    await init_db()

    conn = await get_connection()
    try:
        if target in ("all", "uniqlo"):
            await scrape_uniqlo_jp(conn)
            await scrape_uniqlo_tw(conn)
            await lookup_missing_jp(conn)

        if target in ("all", "gu"):
            await scrape_gu_jp(conn)
            await scrape_gu_tw(conn)

        if target in ("all", "newbalance"):
            await scrape_newbalance_jp(conn)
            await scrape_newbalance_tw(conn)
    finally:
        await conn.close()

    print("\nAll done.")


if __name__ == "__main__":
    asyncio.run(main())
