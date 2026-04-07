"use client"

import { useRouter } from "next/navigation"

export default function BackButton() {
  const router = useRouter()
  return (
    <button
      onClick={() => router.back()}
      className="text-blue-600 text-sm hover:underline"
    >
      ← 返回列表
    </button>
  )
}
