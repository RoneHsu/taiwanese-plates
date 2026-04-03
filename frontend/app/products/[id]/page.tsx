import { getProduct, getExchangeRate } from "@/lib/api"
import Link from "next/link"
import ColorPicker from "@/components/ColorPicker"

interface Props {
  params: Promise<{ id: string }>
}

export default async function ProductPage({ params }: Props) {
  const { id } = await params
  const [product, rateRes] = await Promise.all([
    getProduct(Number(id)),
    getExchangeRate(),
  ])

  const isCheaperInJapan = product.diff_twd > 0

  return (
    <main className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-3xl mx-auto px-4 py-3 flex items-center gap-3">
          <Link href="/" className="text-blue-600 text-sm hover:underline">
            ← 返回列表
          </Link>
          <span className="text-gray-300">|</span>
          <span className="text-lg font-bold text-gray-900">Taiwanese Plates</span>
        </div>
      </header>

      <div className="max-w-3xl mx-auto px-4 py-8">
        <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
          {/* Image + Color Picker */}
          <div className="p-4 pb-0">
            {product.colors && product.colors.length > 0 ? (
              <ColorPicker
                productId={product.uniqlo_product_id}
                colors={product.colors}
                initialImageUrl={product.image_url}
              />
            ) : (
              <div className="bg-gray-100 h-64 flex items-center justify-center">
                {product.image_url ? (
                  <img
                    src={product.image_url}
                    alt={product.name_tw || product.name_jp}
                    className="h-full w-full object-contain"
                  />
                ) : (
                  <span className="text-gray-400">No Image</span>
                )}
              </div>
            )}
          </div>

          <div className="p-6 space-y-6">
            {/* Names */}
            <div>
              <h1 className="text-xl font-bold text-gray-900">
                {product.name_tw || product.name_jp}
              </h1>
              <div className="mt-2 space-y-1.5">
                <p className="text-xs text-gray-400">編號：{product.uniqlo_product_id}</p>
                {/* 尺寸 chips */}
                {product.sizes && (
                  <div className="flex flex-wrap gap-1">
                    {(() => {
                      const sizeOrder = ["XS","S","M","L","XL","XXL","3XL","4XL"]
                      const parts = product.sizes!.split(" ~ ")
                      if (parts.length === 2) {
                        const start = sizeOrder.indexOf(parts[0])
                        const end = sizeOrder.indexOf(parts[1])
                        const range = start !== -1 && end !== -1
                          ? sizeOrder.slice(start, end + 1)
                          : [product.sizes!]
                        return range.map(s => (
                          <span key={s} className="text-xs border border-gray-300 rounded px-2 py-0.5 text-gray-600 bg-white">
                            {s}
                          </span>
                        ))
                      }
                      return (
                        <span className="text-xs border border-gray-300 rounded px-2 py-0.5 text-gray-600 bg-white">
                          {product.sizes}
                        </span>
                      )
                    })()}
                  </div>
                )}
              </div>
            </div>

            {/* Price comparison */}
            <div className="bg-gray-50 rounded-xl p-4 space-y-3">
              <h2 className="text-sm font-semibold text-gray-600 uppercase tracking-wide">
                價格比較
              </h2>

              <div className="flex justify-between items-center py-2 border-b border-gray-200">
                <span className="text-gray-700">🇯🇵 日本售價</span>
                <div className="text-right">
                  <p className="font-bold text-lg">¥{product.jp_price_jpy.toLocaleString()}</p>
                  <p className="text-xs text-gray-400">
                    ≈ NT${product.jp_price_twd.toLocaleString()}（匯率 {rateRes.rate.toFixed(4)}）
                  </p>
                </div>
              </div>

              <div className="flex justify-between items-center py-2 border-b border-gray-200">
                <span className="text-gray-700">🇹🇼 台灣售價</span>
                <p className="font-bold text-lg">NT${product.tw_price_twd.toLocaleString()}</p>
              </div>

              <div className={`flex justify-between items-center py-2 rounded-lg px-3 ${
                isCheaperInJapan ? "bg-red-50" : "bg-green-50"
              }`}>
                <span className="font-semibold text-gray-700">差異</span>
                <div className="text-right">
                  <p className={`font-bold text-lg ${isCheaperInJapan ? "text-red-600" : "text-green-600"}`}>
                    {isCheaperInJapan ? "+" : "-"}NT${Math.abs(product.diff_twd).toLocaleString()}
                  </p>
                  <p className="text-xs text-gray-500">
                    {isCheaperInJapan
                      ? `台灣貴 ${product.diff_pct}%`
                      : `日本貴 ${Math.abs(product.diff_pct)}%`}
                  </p>
                </div>
              </div>
            </div>

            {/* Suggestion */}
            <div className={`rounded-xl p-4 ${isCheaperInJapan ? "bg-blue-50 border border-blue-200" : "bg-green-50 border border-green-200"}`}>
              <p className="text-sm font-medium text-gray-800">
                💡 {product.suggestion}
              </p>
            </div>

            {/* Buy links */}
            <div className="flex gap-3">
              <a
                href={product.jp_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex-1 text-center bg-red-600 text-white py-3 rounded-xl font-medium hover:bg-red-700 transition-colors text-sm"
              >
                🇯🇵 前往日本官網購買
              </a>
              <a
                href={product.tw_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex-1 text-center bg-gray-800 text-white py-3 rounded-xl font-medium hover:bg-gray-900 transition-colors text-sm"
              >
                🇹🇼 前往台灣官網購買
              </a>
            </div>
          </div>
        </div>
      </div>
    </main>
  )
}
