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
]

const ALL_CATEGORIES = [
  { value: "", label: "全部", brands: ["", "uniqlo", "gu"] },
  { value: "men", label: "男裝", brands: ["", "uniqlo", "gu"] },
  { value: "women", label: "女裝", brands: ["", "uniqlo", "gu"] },
  { value: "unisex", label: "男女適穿", brands: ["", "uniqlo", "gu"] },
  { value: "kids", label: "童裝", brands: ["", "uniqlo", "gu"] },
  { value: "baby", label: "嬰兒", brands: ["", "uniqlo"] },
]

interface PageProps {
  searchParams: Promise<{ q?: string; brand?: string; category?: string; sort?: string; offset?: string }>
}

export default async function Home({ searchParams }: PageProps) {
  const params = await searchParams
  const sort = params.sort || "diff_desc"
  const offset = Number(params.offset || 0)
  const limit = 24

  const [productsRes, rateRes] = await Promise.all([
    getProducts({ q: params.q, brand: params.brand, category: params.category, sort, limit, offset }),
    getExchangeRate(),
  ])

  const { data: products, meta } = productsRes
  const rate = rateRes.rate

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
            const active = (params.brand || "") === b.value
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

        {/* Category + Sort filters */}
        <div className="flex flex-wrap gap-2 items-center justify-between">
          <div className="flex gap-1 flex-wrap">
            {ALL_CATEGORIES.filter(cat => cat.brands.includes(params.brand || "")).map((cat) => {
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
    </main>
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
