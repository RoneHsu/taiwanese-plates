import type { Product, ProductsResponse, ExchangeRate } from "@/types"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export async function getProducts(params: {
  q?: string
  category?: string
  sort?: string
  limit?: number
  offset?: number
}): Promise<ProductsResponse> {
  const search = new URLSearchParams()
  if (params.q) search.set("q", params.q)
  if (params.category) search.set("category", params.category)
  if (params.sort) search.set("sort", params.sort)
  if (params.limit) search.set("limit", String(params.limit))
  if (params.offset) search.set("offset", String(params.offset))

  const res = await fetch(`${API_URL}/api/v1/products?${search}`, {
    cache: "no-store",
  })
  if (!res.ok) throw new Error("Failed to fetch products")
  return res.json()
}

export async function getProduct(id: number): Promise<Product> {
  const res = await fetch(`${API_URL}/api/v1/products/${id}`, {
    cache: "no-store",
  })
  if (!res.ok) throw new Error("Product not found")
  return res.json()
}

export async function getExchangeRate(): Promise<ExchangeRate> {
  const res = await fetch(`${API_URL}/api/v1/exchange-rate`, {
    next: { revalidate: 3600 },  // 匯率每小時更新一次即可
  })
  if (!res.ok) throw new Error("Failed to fetch exchange rate")
  return res.json()
}
