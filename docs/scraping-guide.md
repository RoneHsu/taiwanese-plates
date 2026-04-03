# 爬蟲實作指南

以 Uniqlo 為範例，說明爬蟲的設計模式與實作細節。
新增品牌時可參考此文件了解現有架構。

---

## 核心設計原則

1. **內部 API 優先** — 先確認品牌官網是否有內部 REST API（Chrome DevTools → Network），能用 API 就不用 Playwright
2. **非同步爬取** — 使用 `httpx.AsyncClient` + `asyncio`，速度快且記憶體效率高
3. **禮貌爬取** — 每頁請求後 `await asyncio.sleep(0.5)` 避免被封鎖
4. **Upsert 策略** — 使用 `INSERT ... ON CONFLICT ... DO UPDATE`，重跑不怕重複
5. **標準化函數** — 每個爬蟲有 `normalize_xx()` 函數，把 API 回應轉成統一 schema

---

## Uniqlo Japan

### API 資訊
- **端點**: `GET https://www.uniqlo.com/jp/api/commerce/v5/ja/products`
- **類型**: 官方內部 REST API（無需認證）
- **分頁**: offset-based（每頁 36 筆）

### 分類路徑 ID

| 分類 | path 參數 |
|------|-----------|
| 男裝 | `1072` |
| 女裝 | `1073` |
| 童裝 | `1074` |
| 嬰兒 | `1076` |

### 請求範例
```python
GET https://www.uniqlo.com/jp/api/commerce/v5/ja/products
  ?path=1072
  &limit=36
  &offset=0
  &httpFailure=true
```

### 回應結構
```json
{
  "result": {
    "pagination": { "total": 874 },
    "items": [
      {
        "l1Id": "481608",              // 全球商品 ID（配對用）
        "name": "シームレスダウンジャケット",
        "prices": {
          "base": { "value": 8990 },
          "promo": { "value": 7990 }   // 促銷價優先
        },
        "images": {
          "main": {
            "30": { "image": "https://image.uniqlo.com/..." }
          }
        }
      }
    ]
  }
}
```

### 關鍵欄位對應

| API 欄位 | DB 欄位 | 說明 |
|---------|---------|------|
| `l1Id` | `uniqlo_product_id` | 全球商品 ID |
| `name` | `name_jp` | 日文商品名 |
| `prices.promo.value` | `prices.price` | 促銷價（優先） |
| `prices.base.value` | `prices.price` | 原價（fallback） |
| `images.main.{colorCode}.image` | `image_url` | 第一個顏色的圖 |

---

## Uniqlo Taiwan

### API 資訊
- **端點**: `POST https://d.uniqlo.com/tw/p/search/products/by-category`
- **類型**: 官方內部 REST API（無需認證）
- **分頁**: page-based（每頁 36 筆）

### 請求範例
```python
POST https://d.uniqlo.com/tw/p/search/products/by-category
Content-Type: application/json

{
  "categoryCode": "all_men-outer",
  "pageInfo": { "page": 1, "pageSize": 36 }
}
```

### 回應結構
```json
{
  "success": true,
  "resp": [
    {
      "productSum": 61,
      "productList": [
        {
          "masterSpuCode": "481608",    // 全球商品 ID（與 JP l1Id 相同）
          "productName": "男裝 防風無縫羽絨外套",
          "minPrice": 2990,
          "minVaryPrice": 2490,          // 促銷價
          "mainPic": "/tw/hmall/goods/.../3x4.jpg",
          "styleText": ["01 OFF WHITE", "09 BLACK"],
          "minSize": "XS",
          "maxSize": "3XL"
        }
      ]
    }
  ]
}
```

### 關鍵欄位對應

| API 欄位 | DB 欄位 | 說明 |
|---------|---------|------|
| `masterSpuCode` | `uniqlo_product_id` | 全球商品 ID |
| `productName` | `name_tw` | 中文商品名 |
| `minVaryPrice` | `prices.price` | 促銷價（優先） |
| `minPrice` | `prices.price` | 原價（fallback） |
| `styleText` | `products.colors` | 顏色列表，解析為 `01:OFF WHITE/09:BLACK` |
| `minSize` ~ `maxSize` | `products.sizes` | 尺寸範圍，如 `XS ~ 3XL` |

### 顏色格式解析

TW API 回傳 `["01 OFF WHITE", "09 BLACK"]`，
爬蟲解析為 `"01:OFF WHITE/09:BLACK"` 存入 DB，
後端 `parse_colors()` 再轉為 `[{"code":"01","name":"OFF WHITE"}]`。

---

## 資料流程

```
品牌爬蟲（JP / TW）
  ↓ AsyncGenerator[dict]
main.py: upsert_product()
  → INSERT INTO products ON CONFLICT (uniqlo_product_id) DO UPDATE
  → 回傳 product DB id
main.py: insert_price()
  → INSERT INTO prices (product_id, region, price, currency)
```

### JP + TW 合併邏輯

同一個 `uniqlo_product_id` 會被 upsert 到同一列：
- JP 爬蟲寫入：`name_jp`, `image_url`（JP CDN）
- TW 爬蟲寫入：`name_tw`, `colors`, `sizes`
- `image_url` 以 JP CDN 為主（JP 先跑，TW 不覆蓋已有的圖片 URL）

### TW-only 商品補查

TW 爬完後，`lookup_missing_jp()` 會找出只有 TW 價格的商品，
逐一用 `product_id` 查詢 JP API，補入 JP 價格。

---

## 匯率更新

- **來源**: `https://open.er-api.com/v6/latest/JPY`（免費，無需 key）
- **執行**: `scraper/exchange_rate.py`
- **頻率**: 每天隨爬蟲一起執行（GitHub Actions）
- **儲存**: 每次執行新增一筆到 `exchange_rates` 表

---

## 本地開發

```bash
cd scraper
pip install -r requirements.txt

# 設定環境變數
cp .env.example .env
# 編輯 .env 填入 DATABASE_URL

# 執行爬蟲
python main.py

# 只更新匯率
python exchange_rate.py
```

---

## 注意事項

- Uniqlo API 無需登入，但有 rate limit，每次請求間隔 0.5 秒
- JP API 分頁用 `offset`；TW API 分頁用 `page`（從 1 開始）
- TW 的 `mainPic` 是相對路徑，要加前綴 `https://www.uniqlo.com`
- 前端顯示的顏色圖片用 JP CDN URL，不依賴 TW 的 `mainPic`
