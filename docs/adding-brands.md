# 新增品牌 SOP

新增品牌時請按照此步驟進行，以 Uniqlo 實作為參考範例。

---

## Phase 規劃

| Phase | 品牌 | 配對方式 | 狀態 |
|-------|------|---------|------|
| 1 | Uniqlo JP + TW | 全球商品 ID（`l1Id` = `masterSpuCode`） | ✅ 完成 |
| 2 | GU JP + TW | 全球商品 ID（架構與 Uniqlo 相似） | 待開發 |
| 2 | Muji JP + TW | JAN Code 或品牌+型號 | 待開發 |
| 3 | Amazon JP / 樂天 | JAN Code → 品牌+型號 → 名稱相似度 | 未規劃 |
| 3 | Momo / PChome | 爬蟲 + JAN Code 配對 | 未規劃 |

---

## 新增品牌步驟

### Step 1 — 研究 API

1. 用 Chrome DevTools → Network 觀察品牌官網的請求
2. 尋找商品列表的 API 端點（通常是 `/api/products` 或類似路徑）
3. 確認：
   - 是否需要認證？（Cookie / Token）
   - 分頁方式（offset 或 page）
   - 商品 ID 格式（用於日台配對）
   - 價格欄位（原價 / 促銷價）
   - 圖片 URL 格式
   - 顏色、尺寸資料結構

### Step 2 — 建立爬蟲檔案

在 `scraper/` 建立新檔案，例如 `gu_jp.py` 和 `gu_tw.py`：

```python
# scraper/gu_jp.py 範例結構

BASE_URL = "https://..."
HEADERS = { "User-Agent": "..." }
PAGE_SIZE = 36

async def scrape_all_gu_jp() -> AsyncGenerator[dict, None]:
    """爬取所有商品，yield 標準化 dict"""
    ...

def normalize_gu_jp(item: dict, gender: str) -> dict:
    """轉換 API 回應為統一 schema"""
    return {
        "brand": "GU",                  # 新增 brand 欄位
        "uniqlo_product_id": ...,       # 改名為 brand_product_id 或統一用 product_id
        "name_jp": ...,
        "category": gender,
        "image_url": ...,
        "region": "JP",
        "price": ...,
        "currency": "JPY",
    }
```

### Step 3 — 更新資料庫 Schema

若要支援多品牌，需要修改 `products` 資料表：

```sql
-- 新增 brand 欄位
ALTER TABLE products ADD COLUMN brand TEXT NOT NULL DEFAULT 'UNIQLO';

-- 配對 key 改為 (brand, product_id) 唯一
ALTER TABLE products DROP CONSTRAINT products_uniqlo_product_id_key;
ALTER TABLE products ADD CONSTRAINT products_brand_product_id_key
    UNIQUE (brand, uniqlo_product_id);
```

> **注意**: 修改 schema 前請確認不影響現有 Uniqlo 資料

### Step 4 — 更新 scraper/main.py

在 `upsert_product()` 加入 brand 支援：

```python
async def upsert_product(conn, product: dict) -> int:
    brand = product.get("brand", "UNIQLO")
    # INSERT ... ON CONFLICT (brand, uniqlo_product_id) DO UPDATE ...
```

在 `main()` 加入新品牌的爬蟲呼叫：

```python
async def main():
    await init_db()
    conn = await get_connection()
    try:
        await scrape_jp(conn)       # Uniqlo JP
        await scrape_tw(conn)       # Uniqlo TW
        await scrape_gu_jp(conn)    # GU JP（新增）
        await scrape_gu_tw(conn)    # GU TW（新增）
    finally:
        await conn.close()
```

### Step 5 — 更新後端 API

在 `backend/main.py` 的查詢加入 brand 過濾：

```python
# GET /api/v1/products 新增 brand 參數
brand: str | None = Query(None)

# SQL 加入 WHERE brand = $n
```

### Step 6 — 更新前端

在 `frontend/app/page.tsx` 加入品牌切換 Tab 或篩選器。

---

## 商品配對策略

不同品牌的配對難度不同：

### 方法一：全球商品 ID（最簡單）

適用品牌：Uniqlo、GU（同屬 Fast Retailing 集團，ID 格式相同）

```
JP API l1Id = TW API masterSpuCode
直接用 ON CONFLICT (brand, product_id) 合併
```

### 方法二：JAN Code（條碼）

適用品牌：Muji、一般電商

```
JP 商品 JAN Code = TW 商品 JAN Code
需要從 API 或爬蟲取得 JAN Code
```

### 方法三：品牌 + 型號

```python
# 正規化後比對
normalize_name("ウルトラライトダウン") == normalize_name("輕暖羽絨背心")
```

### 方法四：名稱相似度（Phase 3，成本高）

```python
# 使用 difflib 或 embedding
from difflib import SequenceMatcher
similarity = SequenceMatcher(None, name_jp, name_tw).ratio()
```

---

## GU 快速參考

GU 是 Uniqlo 的姐妹品牌，API 架構非常相似：

- **JP API**: `https://www.gu-global.com/jp/api/commerce/v5/ja/products`
- **TW API**: 待確認（可能是 `https://d.gu-global.com/tw/...`）
- **商品 ID**: 同樣使用 `l1Id` / `masterSpuCode`（推測，需驗證）
- **圖片 CDN**: `https://image.uniqlo.com/GU/ST3/jp/imagesgoods/...`（推測）

---

## 注意事項

- 新增品牌前先確認該品牌在台灣有官方銷售渠道
- 確認爬取行為是否符合品牌網站的 Terms of Service
- 爬蟲延遲設定 `asyncio.sleep(0.5)` 以上，避免對伺服器造成負擔
- 所有新爬蟲都要遵循現有的 `normalize_xx()` 標準化模式
