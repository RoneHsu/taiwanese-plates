"""
一次性遷移腳本：本地 PostgreSQL → Supabase
執行一次即可，之後刪除
"""
import asyncio
import ssl
import asyncpg

LOCAL_URL = "postgresql://compare:compare123@localhost:5432/compare_money"
SUPABASE_URL = "postgresql://postgres:RoneHsu85815@db.etzzombesonkpskonyie.supabase.co:5432/postgres"


async def migrate():
    print("連線到本地資料庫...")
    local = await asyncpg.connect(LOCAL_URL)

    print("連線到 Supabase...")
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    remote = await asyncpg.connect(SUPABASE_URL, ssl=ssl_ctx)

    try:
        # 建立 Schema
        print("建立資料表...")
        await remote.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                uniqlo_product_id TEXT UNIQUE NOT NULL,
                name_jp TEXT,
                name_tw TEXT,
                category TEXT,
                image_url TEXT,
                colors TEXT,
                sizes TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS prices (
                id SERIAL PRIMARY KEY,
                product_id INTEGER REFERENCES products(id),
                region TEXT NOT NULL,
                price INTEGER NOT NULL,
                currency TEXT NOT NULL,
                scraped_at TIMESTAMPTZ DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS exchange_rates (
                id SERIAL PRIMARY KEY,
                from_currency TEXT NOT NULL,
                to_currency TEXT NOT NULL,
                rate NUMERIC NOT NULL,
                fetched_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)

        # 遷移 products
        print("遷移 products...")
        products = await local.fetch("SELECT * FROM products ORDER BY id")
        print(f"  共 {len(products)} 筆商品")
        if products:
            await remote.executemany("""
                INSERT INTO products
                    (id, uniqlo_product_id, name_jp, name_tw, category, image_url, colors, sizes, created_at, updated_at)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
                ON CONFLICT (uniqlo_product_id) DO NOTHING
            """, [
                (r["id"], r["uniqlo_product_id"], r["name_jp"], r["name_tw"],
                 r["category"], r["image_url"], r["colors"], r["sizes"],
                 r["created_at"], r["updated_at"])
                for r in products
            ])
            # 同步 sequence
            max_id = max(r["id"] for r in products)
            await remote.execute(f"SELECT setval('products_id_seq', {max_id})")

        # 遷移 prices
        print("遷移 prices...")
        prices = await local.fetch("SELECT * FROM prices ORDER BY id")
        print(f"  共 {len(prices)} 筆價格")
        if prices:
            await remote.executemany("""
                INSERT INTO prices (id, product_id, region, price, currency, scraped_at)
                VALUES ($1,$2,$3,$4,$5,$6)
                ON CONFLICT DO NOTHING
            """, [
                (r["id"], r["product_id"], r["region"], r["price"],
                 r["currency"], r["scraped_at"])
                for r in prices
            ])
            max_id = max(r["id"] for r in prices)
            await remote.execute(f"SELECT setval('prices_id_seq', {max_id})")

        # 遷移 exchange_rates
        print("遷移 exchange_rates...")
        rates = await local.fetch("SELECT * FROM exchange_rates ORDER BY id")
        print(f"  共 {len(rates)} 筆匯率")
        if rates:
            await remote.executemany("""
                INSERT INTO exchange_rates (id, from_currency, to_currency, rate, fetched_at)
                VALUES ($1,$2,$3,$4,$5)
                ON CONFLICT DO NOTHING
            """, [
                (r["id"], r["from_currency"], r["to_currency"], r["rate"], r["fetched_at"])
                for r in rates
            ])

        print("\n✅ 遷移完成！")

        # 驗證
        count = await remote.fetchval("SELECT COUNT(*) FROM products")
        print(f"   Supabase products: {count} 筆")

    finally:
        await local.close()
        await remote.close()


asyncio.run(migrate())
