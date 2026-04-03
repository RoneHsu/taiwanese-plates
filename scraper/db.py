import asyncpg
import os
import ssl
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


def _get_ssl():
    if os.getenv("DATABASE_SSL", "false").lower() == "true":
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    return None


async def get_connection():
    return await asyncpg.connect(DATABASE_URL, ssl=_get_ssl())


async def init_db():
    conn = await get_connection()
    try:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                uniqlo_product_id TEXT UNIQUE NOT NULL,
                name_jp TEXT,
                name_tw TEXT,
                category TEXT,
                image_url TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS prices (
                id SERIAL PRIMARY KEY,
                product_id INTEGER REFERENCES products(id),
                region TEXT NOT NULL,
                price INTEGER NOT NULL,
                currency TEXT NOT NULL,
                scraped_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS exchange_rates (
                id SERIAL PRIMARY KEY,
                from_currency TEXT NOT NULL,
                to_currency TEXT NOT NULL,
                rate NUMERIC(10, 4) NOT NULL,
                fetched_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        # Index for fast product lookup
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_prices_product_id ON prices(product_id);
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_prices_scraped_at ON prices(scraped_at);
        """)

        print("Database initialized.")
    finally:
        await conn.close()
