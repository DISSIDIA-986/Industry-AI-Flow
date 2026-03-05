'use client'

import { ReactNode } from 'react'

interface DashboardShellProps {
  children: ReactNode
}

export default function DashboardShell({ children }: DashboardShellProps) {
  return (
    <div className="flex-1 min-h-0 overflow-auto">
      <div className="shell-main-simple h-full">
        <div className="shell-content h-full">
          {children}
        </div>
      </div>
    </div>
  )
}
