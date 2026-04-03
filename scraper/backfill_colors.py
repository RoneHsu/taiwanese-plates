"""
Backfill colors column with code:name format by re-scraping TW API.
Usage: python backfill_colors.py
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

from uniqlo_tw import scrape_all_tw

load_dotenv()


async def main():
    conn = await asyncpg.connect(os.getenv("DATABASE_URL"))

    print("Starting colors backfill...")
    updated = 0

    async for product in scrape_all_tw():
        pid = product.get("uniqlo_product_id")
        colors = product.get("colors")
        if not pid or not colors:
            continue

        # Only update if new value has codes (contains ":")
        if ":" not in colors:
            continue

        result = await conn.execute(
            "UPDATE products SET colors = $1 WHERE uniqlo_product_id = $2",
            colors, pid
        )
        if result == "UPDATE 1":
            updated += 1
            if updated % 100 == 0:
                print(f"Updated {updated} products...")

    await conn.close()
    print(f"Done. {updated} products updated with color codes.")


if __name__ == "__main__":
    asyncio.run(main())
