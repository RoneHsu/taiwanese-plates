export interface ProductColor {
  code: string
  name: string
}

export interface Product {
  id: number
  uniqlo_product_id: string
  name_jp: string
  name_tw: string
  category: string
  image_url: string | null
  colors: ProductColor[] | null
  sizes: string | null
  jp_price_jpy: number
  jp_price_twd: number
  tw_price_twd: number
  diff_twd: number
  diff_pct: number
  suggestion: string
  jp_url?: string
  tw_url?: string
}

export interface ProductsResponse {
  data: Product[]
  meta: {
    total: number
    limit: number
    offset: number
    exchange_rate: number
  }
}

export interface ExchangeRate {
  from: string
  to: string
  rate: number
  fetched_at: string
}
