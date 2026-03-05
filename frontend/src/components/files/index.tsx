'use client'

import { useState, useCallback } from 'react'

interface FileUploadProps {
  onFileSelect?: (file: File) => void
  onFilesSelected?: (files: File[]) => void
  accept?: string
  maxSize?: number // in MB
  multiple?: boolean
  label?: string
  helpText?: string
  error?: string
  className?: string
}

export function FileUpload({ 
  onFileSelect,
  onFilesSelected,
  accept = '.csv,.xlsx,.xls,.pdf,.txt,.json',
  maxSize = 10, // 10MB
  multiple = false,
  label = 'Select file',
  helpText,
  error,
  className = '' 
}: FileUploadProps) {
  const [dragActive, setDragActive] = useState(false)
  const [fileName, setFileName] = useState<string>('')

  const validateFile = useCallback((file: File): string | null => {
    if (maxSize && file.size > maxSize * 1024 * 1024) {
      return `File size cannot exceed ${maxSize}MB`
    }
    
    if (accept) {
      const acceptedTypes = accept.split(',').map(type => type.trim())
      const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase()
      if (!acceptedTypes.includes(fileExtension)) {
        return `Only the following formats are supported: ${accept}`
      }
    }
    
    return null
  }, [accept, maxSize])

  const handleFileSelect = useCallback((files: File[]) => {
    const validFiles: File[] = []
    for (const file of files) {
      const validationError = validateFile(file)
      if (validationError) {
        alert(validationError)
        continue
      }
      validFiles.push(file)
    }

    if (validFiles.length === 0) {
      return
    }

    const selected = multiple ? validFiles : [validFiles[0]]
    setFileName(selected.map((file) => file.name).join(', '))
    onFilesSelected?.(selected)
    if (onFileSelect && selected[0]) {
      onFileSelect(selected[0])
    }
  }, [multiple, onFileSelect, onFilesSelected, validateFile])

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? [])
    if (files.length > 0) {
      handleFileSelect(files)
    }
  }

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    
    const files = Array.from(e.dataTransfer.files ?? [])
    if (files.length > 0) {
      handleFileSelect(files)
    }
  }, [handleFileSelect])

  return (
    <div className={`space-y-2 ${className}`}>
      {label && (
        <label className="block text-sm font-medium text-gray-700">
          {label}
        </label>
      )}
      
      <div
        className={`
          relative border-2 border-dashed rounded-lg p-6
          transition-colors duration-200
          ${dragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300'}
          ${error ? 'border-red-300' : ''}
          hover:border-blue-400
        `}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <input
          type="file"
          accept={accept}
          multiple={multiple}
          onChange={handleChange}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
        />
        
        <div className="text-center">
          <svg
            className="mx-auto h-12 w-12 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
            />
          </svg>
          
          <div className="mt-4">
            <p className="text-sm text-gray-600">
              <span className="font-medium text-blue-600 hover:text-blue-500">
                Click to upload
              </span>{' '}
              Or drag and drop files here
            </p>
            <p className="text-xs text-gray-500 mt-1">
              Supported formats: {accept}, max {maxSize}MB
            </p>
          </div>
          
          {fileName && (
            <div className="mt-4">
              <p className="text-sm text-gray-700">
                Selected: <span className="font-medium">{fileName}</span>
              </p>
            </div>
          )}
        </div>
      </div>
      
      {error && <p className="text-sm text-red-600">{error}</p>}
      {helpText && !error && <p className="text-sm text-gray-500">{helpText}</p>}
    </div>
  )
}

interface FileListProps {
  files: Array<{
    id: string
    name: string
    size: string
    uploadedAt: string
    status?: 'uploading' | 'success' | 'error'
    progress?: number
  }>
  onDelete?: (id: string) => void
  onDownload?: (id: string) => void
  className?: string
}

export function FileList({ 
  files, 
  onDelete, 
  onDownload,
  className = '' 
}: FileListProps) {
  if (files.length === 0) {
    return null
  }

  return (
    <div className={`space-y-2 ${className}`}>
      <h4 className="text-sm font-medium text-gray-700">File uploaded</h4>
      <div className="space-y-2">
        {files.map((file) => (
          <div
            key={file.id}
            className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
          >
            <div className="flex-1 min-w-0">
              <div className="flex items-center space-x-3">
                <div className="flex-shrink-0">
                  <svg className="h-6 w-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {file.name}
                  </p>
                  <div className="flex items-center space-x-4 text-xs text-gray-500">
                    <span>{file.size}</span>
                    <span>{file.uploadedAt}</span>
                    {file.status === 'uploading' && (
                      <span className="text-blue-600">Uploading...</span>
                    )}
                    {file.status === 'error' && (
                      <span className="text-red-600">Upload failed</span>
                    )}
                  </div>
                </div>
              </div>
              
              {file.status === 'uploading' && file.progress !== undefined && (
                <div className="mt-2">
                  <div className="w-full bg-gray-200 rounded-full h-1">
                    <div
                      className="bg-blue-600 h-1 rounded-full transition-all duration-300"
                      style={{ width: `${file.progress}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
            
            <div className="flex items-center space-x-2 ml-4">
              {onDownload && (
                <button
                  onClick={() => onDownload(file.id)}
                  className="text-gray-400 hover:text-gray-600"
                  title="download"
                >
                  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                </button>
              )}
              {onDelete && (
                <button
                  onClick={() => onDelete(file.id)}
                  className="text-gray-400 hover:text-red-600"
                  title="delete"
                >
                  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default {
  FileUpload,
  FileList
}
