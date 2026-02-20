'use client'

interface ProgressProps {
  value: number
  max?: number
  className?: string
}

export function Progress({ value, max = 100, className = '' }: ProgressProps) {
  const clamped = Math.min(max, Math.max(0, value))
  const percent = (clamped / max) * 100

  return (
    <div className={`h-2 w-full rounded-full bg-gray-200 ${className}`}>
      <div
        className="h-2 rounded-full bg-blue-600 transition-all duration-300"
        style={{ width: `${percent}%` }}
      />
    </div>
  )
}

