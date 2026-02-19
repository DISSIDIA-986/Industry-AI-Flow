'use client'

import { ReactNode } from 'react'

interface DashboardShellProps {
  children: ReactNode
}

export default function DashboardShell({ children }: DashboardShellProps) {
  return (
    <div className="shell-root">
      <div className="shell-main">
        <div className="shell-content">
          {children}
        </div>
      </div>
    </div>
  )
}