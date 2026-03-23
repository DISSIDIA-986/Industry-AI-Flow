'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

/**
 * Legacy route redirect: /data-dashboard → /overview
 *
 * This page was renamed from "Data Dashboard" to "System Overview" and moved
 * to /overview as the post-login landing page. This redirect preserves
 * bookmarks, documentation links, and demo scripts that reference the old URL.
 */
export default function DataDashboardRedirect() {
  const router = useRouter()

  useEffect(() => {
    router.replace('/overview')
  }, [router])

  return null
}
