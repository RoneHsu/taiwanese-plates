# 系統架構文件

## 專案概覽

日台商品跨國比價網站，蒐集 Uniqlo JP / TW 商品價格，透過即時匯率換算，
呈現同一商品在不同地區的價格差異。

---

## 整體架構

```
GitHub Actions（每日 UTC 00:00）
  └── scraper/main.py
        ├── Uniqlo JP API  →  商品 + JPY 價格
        └── Uniqlo TW API  →  商品 + TWD 價格
              ↓
        Supabase PostgreSQL
              ↓
        Render FastAPI（後端）  ←→  frankfurter.app（匯率）
              ↓
        Vercel Next.js（前端）
```

---

## 技術選型

| 元件 | 技術 | 原因 |
|------|------|------|
| 爬蟲 | Python + httpx（非同步） | Uniqlo 有內部 REST API，不需 Playwright |
| 資料庫 | PostgreSQL（Supabase） | 關聯式，方便跨品牌 JOIN 查詢 |
| 後端 | FastAPI + asyncpg | 高效能非同步，輕量部署 |
| 前端 | Next.js 16 + Tailwind CSS | SSR + 靜態生成，部署到 Vercel 免費 |
| 匯率 | frankfurter.app | 免費、無需 API key、支援 JPY→TWD |
| 排程 | GitHub Actions Cron | 完全免費，每月 2000 分鐘 |

---

## 部署資訊

### 前端 — Vercel
- **URL**: https://taiwanese-plates.vercel.app
- **Repo**: RoneHsu/taiwanese-plates
- **Root Directory**: `frontend`
- **環境變數**:
  - `NEXT_PUBLIC_API_URL` = Render 後端 URL

### 後端 — Render
- **URL**: https://taiwanese-plates.onrender.com
- **Root Directory**: `backend`
- **Python 版本**: 3.12（透過環境變數 `PYTHON_VERSION=3.12.0` 設定）
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- **環境變數**:
  - `DATABASE_URL` = Supabase Session Pooler 連線字串
  - `DATABASE_SSL` = `true`
  - `ALLOWED_ORIGINS` = `https://taiwanese-plates.vercel.app`
  - `PYTHON_VERSION` = `3.12.0`
- **注意**: 免費版閒置 15 分鐘後休眠，冷啟動約 30 秒

### 資料庫 — Supabase
- **Project**: RoneHsu's Project
- **Region**: Northeast Asia (Tokyo)
- **連線方式**: Session Pooler（port 5432）
  - 格式: `postgresql://postgres.[ref]:[password]@aws-1-ap-northeast-1.pooler.supabase.com:5432/postgres`
- **注意**: 使用 Direct Connection 在 Render 上會因 IPv6/IPv4 衝突失敗，必須用 Pooler

### 爬蟲排程 — GitHub Actions
- **設定檔**: `.github/workflows/scraper.yml`
- **排程**: 每天 UTC 00:00（台灣時間早上 8:00）
- **Secrets**: `DATABASE_URL`（Settings → Secrets and variables → Actions）
- **手動觸發**: Actions → Daily Scraper → Run workflow

---

## 資料庫 Schema

```sql
products
  id                  SERIAL PRIMARY KEY
  uniqlo_product_id   TEXT UNIQUE NOT NULL   -- 跨 JP/TW 共用的全球商品 ID
  name_jp             TEXT                   -- 日文名稱（JP API 提供）
  name_tw             TEXT                   -- 中文名稱（TW API 提供）
  category            TEXT                   -- men / women / kids / baby / unisex
  image_url           TEXT                   -- 優先使用 JP CDN 圖片
  colors              TEXT                   -- 格式：'01:OFF WHITE/09:BLACK'
  sizes               TEXT                   -- 格式：'XS ~ XL' 或 'FREE'
  created_at          TIMESTAMPTZ DEFAULT NOW()
  updated_at          TIMESTAMPTZ DEFAULT NOW()

prices
  id          SERIAL PRIMARY KEY
  product_id  INTEGER REFERENCES products(id)
  region      TEXT        -- 'JP' or 'TW'
  price       INTEGER
  currency    TEXT        -- 'JPY' or 'TWD'
  scraped_at  TIMESTAMPTZ DEFAULT NOW()

exchange_rates
  id             SERIAL PRIMARY KEY
  from_currency  TEXT      -- 'JPY'
  to_currency    TEXT      -- 'TWD'
  rate           NUMERIC
  fetched_at     TIMESTAMPTZ DEFAULT NOW()
```

---

## 後端 API 端點

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/health` | 健康檢查 |
| GET | `/api/v1/products` | 商品列表 + 比價資料 |
| GET | `/api/v1/products/{id}` | 單一商品詳細比價 |
| GET | `/api/v1/exchange-rate` | 當日匯率 |

### `/api/v1/products` 查詢參數

| 參數 | 預設 | 說明 |
|------|------|------|
| `q` | — | 關鍵字搜尋 |
| `category` | — | men / women / kids / baby / unisex |
| `sort` | `diff_desc` | diff_desc / diff_asc / price_jp / price_tw |
| `limit` | 20 | 每頁筆數 |
| `offset` | 0 | 分頁偏移 |

---

## 商品配對機制

Uniqlo 的全球商品 ID 在 JP 與 TW 之間是一致的：
- **JP API** 回傳 `l1Id`（數字 ID）
- **TW API** 回傳 `masterSpuCode`（同一個數字）

兩者都存為 `uniqlo_product_id`，透過 `ON CONFLICT (uniqlo_product_id)` 自動合併到同一列。

---

## 圖片 URL 格式

Uniqlo CDN 圖片統一格式：
```
https://image.uniqlo.com/UQ/ST3/jp/imagesgoods/{productId}/item/jpgoods_{colorCode}_{productId}_3x4.jpg
```

前端的 ColorPicker 元件利用此格式，透過切換 colorCode 來更換商品主圖。
