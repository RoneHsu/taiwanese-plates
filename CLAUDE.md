# CLAUDE.md — 日台商品跨國比價網站

此檔案為 Claude Code 的專案說明，每次開啟專案時請依照此文件理解背景與執行步驟。

---

## 專案目標

開發一個「日本商品跨國比價」網站，蒐集日本與台灣各大電商平台的商品價格，透過即時匯率換算，呈現同一商品在不同地區的價格差異，協助消費者判斷是否值得從日本購買。

---

## 技術架構

```
爬蟲（Python + httpx）
  ├── Uniqlo JP API  →  取得商品 + 價格（JPY）
  └── Uniqlo TW API  →  取得商品 + 價格（TWD）
         ↓
   PostgreSQL 資料庫
         ↓
   FastAPI 後端  ←→  匯率 API（frankfurter.app）
         ↓
    Next.js 前端
```

| 元件 | 技術 | 說明 |
|------|------|------|
| 爬蟲 | Python + httpx | Uniqlo 有內部 API，不需 Playwright |
| 資料庫 | PostgreSQL | 部署到 Railway |
| 後端 | FastAPI | 提供比價 REST API |
| 前端 | Next.js | 部署到 Vercel |
| 匯率 | frankfurter.app | 免費、無需 API key |
| 部署 | Vercel + Railway | 初期免費方案 |

---

## 資料庫 Schema

```sql
products
  - id
  - uniqlo_product_id   -- 跨區共用，配對用（Uniqlo 全球 ID 一致）
  - name_jp
  - name_tw
  - category
  - image_url

prices
  - id
  - product_id
  - region              -- 'JP' or 'TW'
  - price
  - currency            -- 'JPY' or 'TWD'
  - scraped_at

exchange_rates
  - id
  - rate                -- JPY → TWD
  - fetched_at
```

---

## 開發步驟（依序執行）

### Step 1 — 爬蟲
- 爬取 Uniqlo JP + TW 的商品列表與價格
- 使用 httpx 非同步請求 Uniqlo 內部 API
- 將資料存入 PostgreSQL
- 檔案位置：`scraper/`

### Step 2 — 匯率
- 串接 frankfurter.app 取得 JPY → TWD 匯率
- 每天自動更新一次，存入 `exchange_rates` 資料表
- 檔案位置：`scraper/exchange_rate.py`

### Step 3 — 後端 API
- FastAPI 提供以下端點：
  - `GET /api/v1/products` — 商品列表 + 比價資料
  - `GET /api/v1/products/{id}` — 單一商品詳細比價
  - `GET /api/v1/exchange-rate` — 當日匯率
- 檔案位置：`backend/`

### Step 4 — 前端
- Next.js 顯示比價表格
- 每筆商品顯示：
  - 商品圖片 + 名稱
  - 日本價格（JPY）→ 換算成台幣
  - 台灣價格（TWD）
  - 差價 + 「日本便宜 X%」標示
  - 連結到 Uniqlo JP / TW 官網
- 檔案位置：`frontend/`

### Step 5 — 排程
- 每天自動重新爬取並更新匯率
- 使用 Railway Cron 或 APScheduler
- 檔案位置：`scraper/scheduler.py`

---

## 商品配對策略

| Phase | 對象 | 配對方式 |
|-------|------|---------|
| Phase 1 | 品牌官網（Uniqlo、GU、Muji） | 官網直連，Uniqlo 全球商品 ID 一致，無需額外配對 |
| Phase 2 | 電商平台（Amazon JP、樂天） | JAN Code（條碼）> 品牌+型號 > 名稱相似度 |
| Phase 3 | 台灣電商（Momo、PChome） | 爬蟲 + JAN Code 配對 |

---

## 前端顯示邏輯範例

```
UNIQLO 極暖輕量羽絨衣
日本價格：¥4,990  →  換算：NT$1,048（依當日匯率 1JPY = 0.21TWD）
台灣價格：NT$1,990
差異：台灣貴 NT$942（90%）
建議：考慮從日本購買
```

---

## 暫時不做（避免過度設計）

- 價格趨勢圖（先有足夠資料再做）
- 用戶帳號 / 收藏功能
- 手機 App
- 其他品牌（Phase 2 以後）
- AI 商品配對（Phase 3 以後，維護成本高）

---

## 部署規劃

| 元件 | 平台 | 費用 |
|------|------|------|
| 前端 Next.js | Vercel | 免費 |
| 後端 FastAPI | Railway | 免費額度 |
| PostgreSQL | Railway | 免費額度 |
| 爬蟲排程 | Railway Cron | 免費額度 |

---

## 開發原則

- 先讓功能跑通，再優化
- 每個 Step 完成後確認可運作再進下一步
- 安全性：不硬寫任何 API key，全部使用環境變數
- 資料庫查詢全部用參數化查詢，避免 SQL injection
- 現階段專注 Uniqlo，不提前擴展到其他品牌

---

## 自動重啟規則

每次修改程式碼後，**必須自動重啟**對應服務，不需等待使用者要求：

- 修改 `frontend/` 任何檔案 → 重啟 Next.js（port 3001）
- 修改 `backend/` 任何檔案 → 重啟 FastAPI（port 8000）
- 修改 `scraper/` 任何檔案 → 不需重啟（手動執行）

### 重啟指令

```bash
# 找出並終止現有 process，再重新啟動
# Next.js（前端，port 3001）
PID=$(netstat -ano | grep ":3001 " | grep LISTENING | awk '{print $5}' | head -1)
[ -n "$PID" ] && taskkill //F //PID $PID 2>/dev/null
cd "c:\Compare money\frontend" && "/c/Program Files/nodejs/node.exe" node_modules/next/dist/bin/next dev --port 3001 &

# FastAPI（後端，port 8000）
PID=$(netstat -ano | grep ":8000 " | grep LISTENING | awk '{print $5}' | head -1)
[ -n "$PID" ] && taskkill //F //PID $PID 2>/dev/null
cd "c:\Compare money\backend" && uvicorn main:app --reload --port 8000 &
```
