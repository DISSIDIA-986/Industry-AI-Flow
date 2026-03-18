'use client'

import { useMemo } from 'react'

interface FileUploadProps {
  onFilesSelected?: (files: File[]) => void
  onFileSelect?: (file: File) => void
  accept?: string
  maxSize?: number
  multiple?: boolean
  label?: string
  helpText?: string
  className?: string
}

function normalizeMaxBytes(maxSize?: number): number {
  if (!maxSize || maxSize <= 0) {
    return 10 * 1024 * 1024
  }
  if (maxSize > 1024) {
    return maxSize
  }
  return maxSize * 1024 * 1024
}

export function FileUpload({
  onFilesSelected,
  onFileSelect,
  accept = '.csv,.xlsx,.xls,.pdf,.txt,.md,.json',
  maxSize,
  multiple = false,
  label = 'Select file',
  helpText,
  className = '',
}: FileUploadProps) {
  const maxBytes = useMemo(() => normalizeMaxBytes(maxSize), [maxSize])

  function validate(files: File[]): File[] {
    const acceptedTypes = accept
      .split(',')
      .map((value) => value.trim().toLowerCase())
      .filter(Boolean)
    return files.filter((file) => {
      const ext = `.${(file.name.split('.').pop() || '').toLowerCase()}`
      const extOk = acceptedTypes.length === 0 || acceptedTypes.includes(ext)
      const sizeOk = file.size <= maxBytes
      return extOk && sizeOk
    })
  }

  return (
    <div className={`space-y-2 ${className}`}>
      <label className="block text-sm font-medium text-gray-700">{label}</label>
      <input
        type="file"
        accept={accept}
        multiple={multiple}
        className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
        onChange={(event) => {
          const files = Array.from(event.target.files ?? [])
          const validFiles = validate(files)
          if (validFiles.length === 0) {
            return
          }
          onFilesSelected?.(validFiles)
          if (!multiple && validFiles[0]) {
            onFileSelect?.(validFiles[0])
          }
        }}
      />
      {helpText ? <p className="text-sm text-gray-500">{helpText}</p> : null}
    </div>
  )
}

