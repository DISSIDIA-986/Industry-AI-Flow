'use client'

import type { ReactNode } from 'react'

import { EmptyState as BaseEmptyState } from '@/components/feedback'

interface EmptyStateProps {
  title: string
  description?: string
  icon?: ReactNode
  action?: ReactNode
  actionLabel?: string
  onAction?: () => void
  className?: string
}

export function EmptyState({
  title,
  description,
  icon,
  action,
  actionLabel,
  onAction,
  className,
}: EmptyStateProps) {
  const resolvedAction =
    action ?? (actionLabel && onAction ? <button onClick={onAction}>{actionLabel}</button> : undefined)

  return (
    <BaseEmptyState
      title={title}
      description={description}
      icon={icon}
      action={resolvedAction}
      className={className}
    />
  )
}

