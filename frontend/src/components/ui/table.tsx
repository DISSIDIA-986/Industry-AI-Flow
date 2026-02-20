'use client'

import type { ReactNode } from 'react'

interface BaseProps {
  children: ReactNode
  className?: string
}

export function Table({ children, className = '' }: BaseProps) {
  return (
    <div className="overflow-x-auto">
      <table className={`min-w-full divide-y divide-gray-200 ${className}`}>{children}</table>
    </div>
  )
}

export function TableHeader({ children, className = '' }: BaseProps) {
  return <thead className={`bg-gray-50 ${className}`}>{children}</thead>
}

export function TableHead({ children, className = '' }: BaseProps) {
  return (
    <th
      className={`px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 ${className}`}
    >
      {children}
    </th>
  )
}

export function TableBody({ children, className = '' }: BaseProps) {
  return <tbody className={`divide-y divide-gray-200 bg-white ${className}`}>{children}</tbody>
}

export function TableRow({ children, className = '' }: BaseProps) {
  return <tr className={className}>{children}</tr>
}

export function TableCell({ children, className = '' }: BaseProps) {
  return <td className={`px-6 py-4 whitespace-nowrap text-sm text-gray-900 ${className}`}>{children}</td>
}

