'use client'

import { ReactNode } from 'react'

interface CardProps {
  children: ReactNode
  className?: string
  onClick?: () => void
}

export function Card({ children, className = '', onClick }: CardProps) {
  return (
    <div 
      className={`
        bg-white rounded-xl shadow-sm border border-gray-200
        ${onClick ? 'cursor-pointer hover:shadow-md transition-shadow' : ''}
        ${className}
      `}
      onClick={onClick}
    >
      {children}
    </div>
  )
}

interface CardHeaderProps {
  children: ReactNode
  className?: string
}

export function CardHeader({ children, className = '' }: CardHeaderProps) {
  return (
    <div className={`px-6 py-4 border-b border-gray-200 ${className}`}>
      {children}
    </div>
  )
}

interface CardTitleProps {
  children: ReactNode
  className?: string
}

export function CardTitle({ children, className = '' }: CardTitleProps) {
  return (
    <h3 className={`text-lg font-semibold text-gray-900 ${className}`}>
      {children}
    </h3>
  )
}

interface CardContentProps {
  children: ReactNode
  className?: string
}

export function CardContent({ children, className = '' }: CardContentProps) {
  return (
    <div className={`px-6 py-4 ${className}`}>
      {children}
    </div>
  )
}

interface CardFooterProps {
  children: ReactNode
  className?: string
}

export function CardFooter({ children, className = '' }: CardFooterProps) {
  return (
    <div className={`px-6 py-4 border-t border-gray-200 ${className}`}>
      {children}
    </div>
  )
}

interface StatCardProps {
  title: string
  value: string | number
  change?: string
  description?: string
  icon?: ReactNode
  trend?: 'up' | 'down' | 'neutral'
  className?: string
}

export function StatCard({ 
  title, 
  value, 
  change, 
  description,
  icon,
  trend = 'neutral',
  className = '' 
}: StatCardProps) {
  const trendColors = {
    up: 'text-green-600',
    down: 'text-red-600',
    neutral: 'text-gray-600'
  }

  return (
    <Card className={`p-6 ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <div className="text-sm font-medium text-gray-500">{title}</div>
        {icon && <div className="text-gray-400">{icon}</div>}
      </div>
      <div className="text-2xl font-bold text-gray-900">{value}</div>
      {(change || description) && (
        <div className={`mt-2 text-sm ${change ? `font-medium ${trendColors[trend]}` : 'text-gray-600'}`}>
          {change ?? description}
        </div>
      )}
    </Card>
  )
}

interface InfoCardProps {
  title: string
  description?: string
  children: ReactNode
  actions?: ReactNode
  className?: string
}

export function InfoCard({ 
  title, 
  description, 
  children, 
  actions,
  className = '' 
}: InfoCardProps) {
  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>{title}</CardTitle>
          {actions && <div>{actions}</div>}
        </div>
        {description && (
          <p className="mt-1 text-sm text-gray-600">{description}</p>
        )}
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  )
}

export default {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  CardFooter,
  StatCard,
  InfoCard
}
