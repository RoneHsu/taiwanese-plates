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
    return await asyncpg.connect(DATABASE_URL, ssl=_get_ssl(), statement_cache_size=0)


async def init_db():
    conn = await get_connection()
    try:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                brand TEXT NOT NULL DEFAULT 'uniqlo',
                uniqlo_product_id TEXT NOT NULL,
                name_jp TEXT,
                name_tw TEXT,
                category TEXT,
                image_url TEXT,
                colors TEXT,
                sizes TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE (brand, uniqlo_product_id)
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

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_prices_product_id ON prices(product_id);
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_prices_scraped_at ON prices(scraped_at);
        """)

        await migrate_db(conn)

        print("Database initialized.")
    finally:
        await conn.close()


async def migrate_db(conn):
    """Apply incremental migrations to existing tables."""
    # Add colors column if missing
    await conn.execute("""
        ALTER TABLE products ADD COLUMN IF NOT EXISTS colors TEXT;
    """)
    # Add sizes column if missing
    await conn.execute("""
        ALTER TABLE products ADD COLUMN IF NOT EXISTS sizes TEXT;
    """)
    # Add brand column (DEFAULT 'uniqlo' covers existing rows)
    await conn.execute("""
        ALTER TABLE products ADD COLUMN IF NOT EXISTS brand TEXT NOT NULL DEFAULT 'uniqlo';
    """)
    # Drop old single-column unique constraint if it exists
    await conn.execute("""
        ALTER TABLE products DROP CONSTRAINT IF EXISTS products_uniqlo_product_id_key;
    """)
    # Add composite unique constraint if it doesn't exist
    await conn.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'products_brand_product_id_key'
            ) THEN
                ALTER TABLE products
                ADD CONSTRAINT products_brand_product_id_key
                UNIQUE (brand, uniqlo_product_id);
            END IF;
        END
        $$;
    """)
