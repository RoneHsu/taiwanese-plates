"use client"

import { useRouter, useSearchParams } from "next/navigation"
import { useState, useTransition } from "react"

export default function SearchBar() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [isPending, startTransition] = useTransition()
  const [value, setValue] = useState(searchParams.get("q") || "")

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const params = new URLSearchParams(searchParams.toString())
    if (value) {
      params.set("q", value)
    } else {
      params.delete("q")
    }
    params.delete("offset")
    startTransition(() => router.push(`/?${params}`))
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="搜尋商品名稱，例如：牛仔褲、T恤..."
        className="flex-1 border border-gray-300 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
      />
      <button
        type="submit"
        disabled={isPending}
        className="bg-blue-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
      >
        {isPending ? "搜尋中..." : "搜尋"}
      </button>
    </form>
  )
}
