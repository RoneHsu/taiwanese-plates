"use client"

import { useState } from "react"
import type { ProductColor } from "@/types"
import { toChineseColor } from "@/lib/colorNames"

interface Props {
  productId: string
  brand: string
  colors: ProductColor[]
  initialImageUrl: string | null
}

export default function ColorPicker({ productId, brand, colors, initialImageUrl }: Props) {
  const buildImageUrl = (code: string) => {
    if (brand === "gu") {
      return `https://image.uniqlo.com/GU/ST3/AsianCommon/imagesgoods/${productId}/item/goods_${code}_${productId}_3x4.jpg`
    }
    return `https://image.uniqlo.com/UQ/ST3/jp/imagesgoods/${productId}/item/jpgoods_${code}_${productId}_3x4.jpg`
  }

  const [selectedCode, setSelectedCode] = useState<string | null>(colors[0]?.code ?? null)
  const [currentImageUrl, setCurrentImageUrl] = useState<string | null>(
    initialImageUrl ?? (colors[0] ? buildImageUrl(colors[0].code) : null)
  )

  const handleSelect = (color: ProductColor) => {
    setSelectedCode(color.code)
    setCurrentImageUrl(buildImageUrl(color.code))
  }

  return (
    <div className="space-y-4">
      {/* Main image */}
      <div className="bg-gray-100 h-64 flex items-center justify-center overflow-hidden">
        {currentImageUrl ? (
          <img
            src={currentImageUrl}
            alt="商品圖片"
            className="h-full w-full object-contain"
          />
        ) : (
          <span className="text-gray-400">No Image</span>
        )}
      </div>

      {/* Color swatches */}
      {colors.length > 0 && (
        <div>
          <p className="text-xs text-gray-500 mb-2">
            顏色：{toChineseColor(colors.find(c => c.code === selectedCode)?.name ?? "")}
          </p>
          <div className="flex flex-wrap gap-2">
            {colors.map(color => (
              <button
                key={color.code}
                onClick={() => handleSelect(color)}
                title={toChineseColor(color.name)}
                className={`w-10 h-10 rounded overflow-hidden border-2 transition-all ${
                  selectedCode === color.code
                    ? "border-gray-900 scale-110"
                    : "border-gray-200 hover:border-gray-400"
                }`}
              >
                <img
                  src={buildImageUrl(color.code)}
                  alt={color.name}
                  className="w-full h-full object-cover"
                  onError={(e) => {
                    const el = e.target as HTMLImageElement
                    el.style.display = "none"
                    el.parentElement!.style.backgroundColor = "#e5e7eb"
                  }}
                />
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
