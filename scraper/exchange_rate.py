"""
Step 2 — Exchange rate fetcher
Source: frankfurter.app (free, no API key needed)

Usage:
    python exchange_rate.py
"""

import asyncio
import httpx
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
EXCHANGE_RATE_URL = "https://open.er-api.com/v6/latest/JPY"


async def fetch_rate(from_currency: str = "JPY", to_currency: str = "TWD") -> float:
    """Fetch latest exchange rate from exchangerate-api.com (free, supports TWD)."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"https://open.er-api.com/v6/latest/{from_currency}")
        resp.raise_for_status()
        data = resp.json()
        return data["rates"][to_currency]


async def save_rate(conn: asyncpg.Connection, from_currency: str, to_currency: str, rate: float):
    await conn.execute("""
        INSERT INTO exchange_rates (from_currency, to_currency, rate)
        VALUES ($1, $2, $3)
    """, from_currency, to_currency, rate)


async def get_latest_rate(conn: asyncpg.Connection, from_currency: str = "JPY", to_currency: str = "TWD") -> float | None:
    """Get most recent rate from DB."""
    row = await conn.fetchrow("""
        SELECT rate FROM exchange_rates
        WHERE from_currency = $1 AND to_currency = $2
        ORDER BY fetched_at DESC
        LIMIT 1
    """, from_currency, to_currency)
    return float(row["rate"]) if row else None


async def update_rate():
    """Fetch and store latest JPY→TWD rate."""
    rate = await fetch_rate("JPY", "TWD")
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await save_rate(conn, "JPY", "TWD", rate)
        print(f"Rate updated: 1 JPY = {rate} TWD")
    finally:
        await conn.close()
    return rate


if __name__ == "__main__":
    asyncio.run(update_rate())
