"use client"

import type { Product } from "@/types"
import Link from "next/link"

interface Props {
  product: Product
  rate: number
}

export default function ProductCard({ product, rate }: Props) {
  const isCheaperInJapan = product.diff_twd > 0
  const diffAbs = Math.abs(product.diff_twd)
  const diffPctAbs = Math.abs(product.diff_pct)

  return (
    <Link href={`/products/${product.id}`}>
      <div className="bg-white rounded-xl border border-gray-200 hover:border-blue-300 hover:shadow-md transition-all p-4 cursor-pointer h-full flex flex-col">
        {/* Image */}
        <div className="bg-gray-100 rounded-lg h-40 flex items-center justify-center mb-3 overflow-hidden">
          {product.image_url ? (
            <img
              src={product.image_url}
              alt={product.name_tw || product.name_jp}
              className="h-full w-full object-cover"
            />
          ) : (
            <span className="text-gray-400 text-sm">No Image</span>
          )}
        </div>

        {/* Name */}
        <p className="text-sm font-semibold text-gray-900 line-clamp-2 mb-1">
          {product.name_tw || product.name_jp}
        </p>

        {/* 商品編號 / 尺寸 / 顏色 */}
        <div className="mb-2 space-y-1.5">
          <p className="text-xs text-gray-400">編號：{product.uniqlo_product_id}</p>

          {/* 尺寸 chip */}
          {product.sizes && (
            <div className="flex flex-wrap gap-1">
              {product.sizes.split(" ~ ").length === 2
                ? (() => {
                    const sizeOrder = ["XS","S","M","L","XL","XXL","3XL","4XL"]
                    const [min, max] = product.sizes!.split(" ~ ")
                    const start = sizeOrder.indexOf(min)
                    const end = sizeOrder.indexOf(max)
                    const range = start !== -1 && end !== -1
                      ? sizeOrder.slice(start, end + 1)
                      : [product.sizes!]
                    return range.map(s => (
                      <span key={s} className="text-xs border border-gray-300 rounded px-1.5 py-0.5 text-gray-600 bg-white">
                        {s}
                      </span>
                    ))
                  })()
                : (
                  <span className="text-xs border border-gray-300 rounded px-1.5 py-0.5 text-gray-600 bg-white">
                    {product.sizes}
                  </span>
                )
              }
            </div>
          )}

          {/* 顏色縮圖 */}
          {product.colors && product.colors.length > 0 && (
            <div className="flex flex-wrap gap-1 items-center">
              {product.colors.slice(0, 6).map(c => (
                <img
                  key={c.code}
                  src={`https://image.uniqlo.com/UQ/ST3/jp/imagesgoods/${product.uniqlo_product_id}/item/jpgoods_${c.code}_${product.uniqlo_product_id}_3x4.jpg`}
                  alt={c.name}
                  title={c.name}
                  className="w-6 h-6 rounded-sm object-cover border border-gray-200"
                  onError={(e) => { (e.target as HTMLImageElement).style.display = "none" }}
                />
              ))}
              {product.colors.length > 6 && (
                <span className="text-xs text-gray-400">+{product.colors.length - 6}</span>
              )}
            </div>
          )}
        </div>

        {/* Price comparison */}
        <div className="mt-auto space-y-1">
          <div className="flex justify-between text-sm">
            <span className="text-gray-700">🇯🇵 日本</span>
            <span className="font-bold text-gray-900">
              ¥{product.jp_price_jpy.toLocaleString()}
              <span className="text-gray-500 text-xs ml-1">
                (≈ NT${product.jp_price_twd.toLocaleString()})
              </span>
            </span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-700">🇹🇼 台灣</span>
            <span className="font-bold text-gray-900">
              NT${product.tw_price_twd.toLocaleString()}
            </span>
          </div>

          {/* Badge */}
          <div className="pt-2">
            {isCheaperInJapan ? (
              <span className="inline-block bg-red-50 text-red-600 text-xs font-medium px-2 py-1 rounded-full">
                台灣貴 {diffPctAbs}% (+NT${diffAbs.toLocaleString()})
              </span>
            ) : (
              <span className="inline-block bg-green-50 text-green-600 text-xs font-medium px-2 py-1 rounded-full">
                日本貴 {diffPctAbs}% (+NT${diffAbs.toLocaleString()})
              </span>
            )}
          </div>
        </div>
      </div>
    </Link>
  )
}
