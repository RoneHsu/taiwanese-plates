# Changelog

所有重要的專案更新都會記錄在此文件。

---

## [2026-04-05]

### 多品牌支援（GU）

- **DB Schema 升級**：`products` 新增 `brand` 欄位（預設 `uniqlo`），唯一鍵改為 `(brand, uniqlo_product_id)`；`migrate_db()` 自動處理現有資料庫升級
- **GU JP 爬蟲**：新增 `scraper/gu_jp.py`，串接 `gu-global.com/jp` API（l1Id: 2256/2257/2258）
- **GU TW 爬蟲**：新增 `scraper/gu_tw.py`，串接 `gu-global.com/tw` API
- **爬蟲入口更新**：`scraper/main.py` 支援 `python main.py [all|uniqlo|gu]` 選擇性執行
- **後端 API 更新**：`/api/v1/products` 新增 `brand` 篩選參數；商品回應加入 `brand` 欄位；GU 商品連結指向正確官網
- **前端品牌 Tab**：首頁頂部新增「全部品牌 / UNIQLO / GU」分頁，點選後切換品牌，下方分類 Tab 保持不變
- **爬蟲執行結果**：GU JP 1,306 件、GU TW 755 件，配對成功 407 件

---

## [2026-04-03]

### 前端改善

- **網站標題可點選**：`Taiwanese Plates` 標題加入連結，點擊後回到首頁初始狀態
- **搜尋欄位清除按鈕**：輸入文字時，欄位右側出現 ✕ 圖示，點擊後清空文字並回到初始頁面
- **Enter 空白搜尋**：搜尋欄位空白時按 Enter，導回初始頁面（而非保留篩選條件）
- **搜尋欄位文字顏色**：輸入文字改為黑色（`text-gray-900`），提升可讀性
- **商品詳細頁金額顏色**：日本售價與台灣售價金額改為黑色，差異欄位維持紅/綠色
