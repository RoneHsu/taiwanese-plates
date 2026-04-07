import { Suspense } from "react"
import { getProducts, getExchangeRate } from "@/lib/api"
import ProductCard from "@/components/ProductCard"
import SearchBar from "@/components/SearchBar"
import Link from "next/link"

const SORT_OPTIONS = [
  { value: "diff_desc", label: "台灣最貴優先" },
  { value: "diff_asc",  label: "日本最貴優先" },
  { value: "price_jp",  label: "日本價格↑" },
  { value: "price_tw",  label: "台灣價格↑" },
]

const BRANDS = [
  { value: "", label: "全部品牌" },
  { value: "uniqlo", label: "UNIQLO" },
  { value: "gu", label: "GU" },
  { value: "newbalance", label: "New Balance" },
]

const BRAND_CARDS = [
  { value: "uniqlo", label: "UNIQLO", desc: "服飾・休閒・機能" },
  { value: "gu", label: "GU", desc: "平價時尚服飾" },
  { value: "newbalance", label: "New Balance", desc: "運動鞋・服飾・配件" },
]

const BRAND_CATEGORIES: Record<string, { value: string; label: string }[]> = {
  uniqlo: [
    { value: "", label: "全部" },
    { value: "men", label: "男裝" },
    { value: "women", label: "女裝" },
    { value: "unisex", label: "男女適穿" },
    { value: "kids", label: "童裝" },
    { value: "baby", label: "嬰兒" },
  ],
  gu: [
    { value: "", label: "全部" },
    { value: "men", label: "男裝" },
    { value: "women", label: "女裝" },
    { value: "unisex", label: "男女適穿" },
    { value: "kids", label: "童裝" },
  ],
  newbalance: [],
}

interface PageProps {
  searchParams: Promise<{ q?: string; brand?: string; category?: string; sort?: string; offset?: string }>
}

export default async function Home({ searchParams }: PageProps) {
  const params = await searchParams
  const brand = params.brand || ""
  const sort = params.sort || "diff_desc"
  const offset = Number(params.offset || 0)
  const limit = 24

  const rateRes = await getExchangeRate()
  const rate = rateRes.rate

  const categories = brand ? (BRAND_CATEGORIES[brand] ?? []) : []

  return (
    <main className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link href="/" className="text-lg font-bold text-gray-900 hover:text-blue-600 transition-colors">
            Taiwanese Plates
          </Link>
          <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded-full">
            匯率 1 JPY = {rate.toFixed(4)} TWD
          </span>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-4 py-6 space-y-5">
        {/* Search */}
        <Suspense>
          <SearchBar />
        </Suspense>

        {/* Brand tabs */}
        <div className="flex gap-2 border-b border-gray-200 pb-2">
          {BRANDS.map((b) => {
            const active = brand === b.value
            const href = buildHref(params, { brand: b.value, category: "", offset: "0" })
            return (
              <Link
                key={b.value}
                href={href}
                className={`px-4 py-1.5 rounded-t text-sm font-semibold transition-colors border-b-2 ${
                  active
                    ? "border-blue-600 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-800"
                }`}
              >
                {b.label}
              </Link>
            )
          })}
        </div>

        {/* 全部品牌：顯示品牌卡片 */}
        {!brand ? (
          <BrandLanding rate={rate} />
        ) : (
          <BrandProducts
            params={params}
            brand={brand}
            sort={sort}
            offset={offset}
            limit={limit}
            categories={categories}
            rate={rate}
          />
        )}
      </div>
    </main>
  )
}

function BrandLanding({ rate }: { rate: number }) {
  return (
    <div className="space-y-6 py-4">
      <p className="text-sm text-gray-500">請選擇品牌查看日台比價</p>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {BRAND_CARDS.map((b) => (
          <Link
            key={b.value}
            href={`/?brand=${b.value}`}
            className="bg-white border border-gray-200 rounded-xl p-6 hover:border-blue-400 hover:shadow-md transition-all group"
          >
            <p className="text-xl font-bold text-gray-900 group-hover:text-blue-600 transition-colors">
              {b.label}
            </p>
            <p className="text-sm text-gray-500 mt-1">{b.desc}</p>
            <p className="text-xs text-blue-500 mt-4 font-medium">查看比價 →</p>
          </Link>
        ))}
      </div>
      <p className="text-xs text-gray-400">匯率 1 JPY = {rate.toFixed(4)} TWD</p>
    </div>
  )
}

async function BrandProducts({
  params,
  brand,
  sort,
  offset,
  limit,
  categories,
  rate,
}: {
  params: Record<string, string | undefined>
  brand: string
  sort: string
  offset: number
  limit: number
  categories: { value: string; label: string }[]
  rate: number
}) {
  const productsRes = await getProducts({
    q: params.q,
    brand,
    category: params.category,
    sort,
    limit,
    offset,
  })
  const { data: products, meta } = productsRes

  return (
    <div className="space-y-4">
      {/* Category + Sort filters */}
      <div className="flex flex-wrap gap-2 items-center justify-between">
        <div className="flex gap-1 flex-wrap">
          {categories.map((cat) => {
            const active = (params.category || "") === cat.value
            const href = buildHref(params, { category: cat.value, offset: "0" })
            return (
              <Link
                key={cat.value}
                href={href}
                className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                  active
                    ? "bg-blue-600 text-white"
                    : "bg-white border border-gray-300 text-gray-600 hover:border-blue-400"
                }`}
              >
                {cat.label}
              </Link>
            )
          })}
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">排序：</span>
          <div className="flex gap-1">
            {SORT_OPTIONS.map((opt) => {
              const active = sort === opt.value
              const href = buildHref(params, { sort: opt.value, offset: "0" })
              return (
                <Link
                  key={opt.value}
                  href={href}
                  className={`px-2 py-1 rounded text-xs font-medium transition-colors ${
                    active
                      ? "bg-blue-600 text-white"
                      : "bg-white border border-gray-300 text-gray-600 hover:border-blue-400"
                  }`}
                >
                  {opt.label}
                </Link>
              )
            })}
          </div>
        </div>
      </div>

      {/* Result count */}
      <p className="text-sm text-gray-500">
        共 {meta.total} 件配對商品
        {params.q && <span>（搜尋：「{params.q}」）</span>}
      </p>

      {/* Product grid */}
      {products.length === 0 ? (
        <div className="text-center py-20 text-gray-400">
          <p className="text-4xl mb-3">🔍</p>
          <p>找不到相關商品</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
          {products.map((product) => (
            <ProductCard key={product.id} product={product} rate={rate} />
          ))}
        </div>
      )}

      {/* Pagination */}
      {meta.total > limit && (
        <div className="flex justify-center gap-2 pt-4">
          {offset > 0 && (
            <Link
              href={buildHref(params, { offset: String(offset - limit) })}
              className="px-4 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-900 hover:border-blue-400"
            >
              ← 上一頁
            </Link>
          )}
          <span className="px-4 py-2 text-sm text-gray-900">
            第 {Math.floor(offset / limit) + 1} / {Math.ceil(meta.total / limit)} 頁
          </span>
          {offset + limit < meta.total && (
            <Link
              href={buildHref(params, { offset: String(offset + limit) })}
              className="px-4 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-900 hover:border-blue-400"
            >
              下一頁 →
            </Link>
          )}
        </div>
      )}
    </div>
  )
}

function buildHref(
  current: Record<string, string | undefined>,
  overrides: Record<string, string>
): string {
  const p = new URLSearchParams()
  const merged = { ...current, ...overrides }
  for (const [k, v] of Object.entries(merged)) {
    if (v) p.set(k, v)
  }
  return `/?${p}`
}
