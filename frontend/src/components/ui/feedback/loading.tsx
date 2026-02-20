'use client'

import { Loading as BaseLoading } from '@/components/feedback'

interface LoadingProps {
  message?: string
  text?: string
  size?: 'sm' | 'md' | 'lg'
  fullScreen?: boolean
}

export function Loading({ message, text, size, fullScreen }: LoadingProps) {
  return <BaseLoading text={message ?? text ?? '加载中...'} size={size} fullScreen={fullScreen} />
}

