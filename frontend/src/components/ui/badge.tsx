'use client'

import type { ReactNode } from 'react'

type BadgeVariant = 'default' | 'secondary' | 'success' | 'warning' | 'destructive' | 'outline'

interface BadgeProps {
  children: ReactNode
  variant?: BadgeVariant
  className?: string
}

const variantClassMap: Record<BadgeVariant, string> = {
  default: 'bg-blue-100 text-blue-800',
  secondary: 'bg-gray-100 text-gray-800',
  success: 'bg-green-100 text-green-800',
  warning: 'bg-amber-100 text-amber-800',
  destructive: 'bg-red-100 text-red-800',
  outline: 'bg-white text-gray-800 border border-gray-300',
}

export function Badge({ children, variant = 'default', className = '' }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ${variantClassMap[variant]} ${className}`}
    >
      {children}
    </span>
  )
}

