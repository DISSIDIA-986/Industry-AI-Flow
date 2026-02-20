'use client'

import type { ReactNode } from 'react'

import { Card as BaseCard, CardContent, CardHeader, CardTitle } from '@/components/cards'

interface CardProps {
  children: ReactNode
  className?: string
  onClick?: () => void
}

interface CardDescriptionProps {
  children: ReactNode
  className?: string
}

export function Card({ children, className, onClick }: CardProps) {
  return (
    <BaseCard className={className} onClick={onClick}>
      {children}
    </BaseCard>
  )
}

export { CardContent, CardHeader, CardTitle }

export function CardDescription({ children, className = '' }: CardDescriptionProps) {
  return <p className={`mt-1 text-sm text-gray-600 ${className}`}>{children}</p>
}

