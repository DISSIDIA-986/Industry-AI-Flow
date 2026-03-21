'use client'

import { useState, useEffect, useRef } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { realApiService } from '@/lib/real-api-client'
import type { RealDocumentListResponse } from '@/lib/real-api-client'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { FileUpload } from '@/components/ui/files/file-upload'
import { Loading } from '@/components/ui/feedback/loading'
import { EmptyState } from '@/components/ui/feedback/empty-state'

interface Document {
  id: string
  name: string
  type: string
  size: string
  uploadedAt: Date
  status: 'processed' | 'processing' | 'error'
  source: 'uploaded' | 'knowledge_base'
  chunkCount?: number
}

const ALLOW_DOCUMENTS_MOCK_FALLBACK =
  process.env.NEXT_PUBLIC_ALLOW_DOCUMENTS_MOCK_FALLBACK === 'true'

function normalizeDocumentStatus(
  rawStatus: RealDocumentListResponse['status'],
): Document['status'] {
  const status = String(rawStatus || '').toLowerCase()
  if (status === 'processed' || status === 'completed') {
    return 'processed'
  }
  if (status === 'processing' || status === 'pending') {
    return 'processing'
  }
  return 'error'
}

function normalizeDocumentSource(
  rawSource: RealDocumentListResponse['source'],
): Document['source'] {
  return String(rawSource || '').toLowerCase() === 'vector_index'
    ? 'knowledge_base'
    : 'uploaded'
}

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(true)
  const [apiStatus, setApiStatus] = useState<'checking' | 'connected' | 'disconnected'>('checking')
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)
  const { user } = useAuth()

  // Load document list
  useEffect(() => {
    loadDocuments()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const loadDocuments = async () => {
    setLoading(true)
    try {
      const health = await realApiService.checkHealth()
      const connected = health.status === 'ok'
      setApiStatus(connected ? 'connected' : 'disconnected')
      if (!connected) {
        setDocuments(ALLOW_DOCUMENTS_MOCK_FALLBACK ? getMockDocuments() : [])
        return
      }

      const realDocs = await realApiService.getDocuments()

      // Convert to front-end format
      const formattedDocs: Document[] = realDocs.map(doc => ({
        id: doc.id,
        name: String(doc.filename || doc.name || 'document'),
        type: String(doc.type || getFileType(String(doc.filename || doc.name || ''))),
        size: formatFileSize(Number(doc.size || 0)),
        uploadedAt: new Date(String(doc.upload_time || doc.uploaded_at || new Date().toISOString())),
        status: normalizeDocumentStatus(doc.status),
        source: normalizeDocumentSource(doc.source),
        chunkCount: Number(doc.chunk_count || 0) || undefined,
      }))

      setDocuments(formattedDocs)

      // Optional local fallback for visual demos only.
      if (formattedDocs.length === 0 && ALLOW_DOCUMENTS_MOCK_FALLBACK) {
        setDocuments(getMockDocuments())
      }
    } catch (error) {
      console.error('Failed to load documents:', error)
      setApiStatus('disconnected')
      if (ALLOW_DOCUMENTS_MOCK_FALLBACK) {
        setDocuments(getMockDocuments())
      } else {
        setDocuments([])
      }
    } finally {
      setLoading(false)
    }
  }

  const getMockDocuments = (): Document[] => [
    {
      id: '1',
      name: 'Construction Cost Estimating Guide.pdf',
      type: 'PDF',
      size: '2.4 MB',
      uploadedAt: new Date('2026-02-13'),
      status: 'processed',
      source: 'uploaded',
    },
    {
      id: '2',
      name: 'Project Risk Assessment Report.docx',
      type: 'Word',
      size: '1.8 MB',
      uploadedAt: new Date('2026-02-12'),
      status: 'processed',
      source: 'uploaded',
    },
    {
      id: '3',
      name: 'Construction Safety Regulations.pdf',
      type: 'PDF',
      size: '3.2 MB',
      uploadedAt: new Date('2026-02-11'),
      status: 'processed',
      source: 'uploaded',
    },
  ]

  const getFileType = (filename: string): string => {
    const ext = filename.split('.').pop()?.toLowerCase()
    switch (ext) {
      case 'pdf': return 'PDF'
      case 'doc':
      case 'docx': return 'Word'
      case 'xls':
      case 'xlsx': return 'Excel'
      case 'ppt':
      case 'pptx': return 'PowerPoint'
      case 'txt': return 'Text'
      case 'jpg':
      case 'jpeg':
      case 'png':
      case 'gif': return 'Image'
      default: return 'File'
    }
  }

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const handleFileSelect = (files: File[]) => {
    setSelectedFiles(files)
  }

  const handleUpload = async () => {
    if (selectedFiles.length === 0) return

    setUploading(true)
    setUploadProgress(0)
    setUploadError(null)

    try {
      // Simulate upload progress
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval)
            return prev
          }
          return prev + 10
        })
      }, 200)

      const failedFiles: string[] = []

      // Upload each file
      for (const file of selectedFiles) {
        try {
          if (apiStatus === 'connected') {
            await realApiService.uploadDocument(file, {
              title: file.name,
              description: `Uploaded by ${user?.name || 'user'}`,
              tags: ['uploaded', getFileType(file.name).toLowerCase()]
            })
          } else {
            await new Promise(resolve => setTimeout(resolve, 1000))
          }
        } catch (error) {
          console.error(`Failed to upload ${file.name}:`, error)
          failedFiles.push(file.name)
        }
      }

      clearInterval(progressInterval)
      setUploadProgress(100)

      if (failedFiles.length > 0) {
        setUploadError(`Failed to upload: ${failedFiles.join(', ')}. Please try again.`)
      }

      // Upload completed, reload the document list
      setTimeout(() => {
        setUploading(false)
        setUploadProgress(0)
        setSelectedFiles([])
        loadDocuments()

        // Reset file input
        if (fileInputRef.current) {
          fileInputRef.current.value = ''
        }
      }, 500)

    } catch (error) {
      console.error('Upload failed:', error)
      setUploadError('Upload failed. Please check your connection and try again.')
      setUploading(false)
      setUploadProgress(0)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this document?')) return

    setDeleteError(null)
    try {
      if (apiStatus === 'connected') {
        await realApiService.deleteDocument(id)
      }
      // Refresh from backend to ensure consistency
      await loadDocuments()
    } catch (error) {
      console.error('Failed to delete document:', error)
      setDeleteError('Failed to delete document. Please try again.')
    }
  }

  const filteredDocuments = documents.filter(doc =>
    doc.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    doc.type.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const getStatusBadge = (status: Document['status']) => {
    switch (status) {
      case 'processed':
        return <Badge variant="success">Processed</Badge>
      case 'processing':
        return <Badge variant="warning">Processing</Badge>
      case 'error':
        return <Badge variant="destructive">Error</Badge>
      default:
        return <Badge variant="secondary">Unknown</Badge>
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Page title and status */}
        <div className="mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Document Management</h1>
              <p className="text-gray-600 mt-2">
                Upload, manage, and process construction project documents
              </p>
            </div>
            <div className="flex items-center space-x-2">
              <div className={`w-2 h-2 rounded-full ${
                apiStatus === 'connected' ? 'bg-green-500' :
                apiStatus === 'disconnected' ? 'bg-red-500' : 'bg-yellow-500'
              }`}></div>
              <span className="text-sm text-gray-600">
                {apiStatus === 'connected' ? 'API Connected' :
                 apiStatus === 'disconnected' ? 'API Disconnected' : 'Checking API...'}
              </span>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: Upload area */}
          <div className="lg:col-span-1">
            <Card>
              <CardHeader>
                <CardTitle>Upload Documents</CardTitle>
                <CardDescription>
                  Supports PDF, Word, Excel, Image, and other formats
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <FileUpload
                    onFilesSelected={handleFileSelect}
                    accept=".pdf,.doc,.docx,.xls,.xlsx,.txt,.md,.jpg,.jpeg,.png"
                    maxSize={50} // 50MB (FileUpload expects MB, not bytes)
                    multiple
                  />

                  {selectedFiles.length > 0 && (
                    <div className="space-y-2">
                      <div className="text-sm font-medium">{selectedFiles.length} file(s) selected:</div>
                      <div className="space-y-1 max-h-40 overflow-y-auto">
                        {selectedFiles.map((file, index) => (
                          <div key={index} className="text-xs text-gray-600 truncate">
                            {file.name} ({formatFileSize(file.size)})
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {uploading && (
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span>Upload Progress</span>
                        <span>{uploadProgress}%</span>
                      </div>
                      <Progress value={uploadProgress} />
                    </div>
                  )}

                  {uploadError && (
                    <div className="text-sm text-red-600 bg-red-50 p-2 rounded">
                      {uploadError}
                    </div>
                  )}

                  <Button
                    onClick={handleUpload}
                    disabled={selectedFiles.length === 0 || uploading}
                    className="w-full"
                  >
                    {uploading ? 'Uploading...' : 'Upload'}
                  </Button>

                  <div className="text-xs text-gray-500">
                    <p>• Maximum file size: 50 MB</p>
                    <p>• Supported: PDF, Word, Excel, Text, Markdown, Images</p>
                    <p>• Documents are automatically processed after upload</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Right: Document list */}
          <div className="lg:col-span-2">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>Document List</CardTitle>
                    <CardDescription>
                      All documents in the knowledge base
                    </CardDescription>
                  </div>
                  <div className="w-64">
                    <Input
                      placeholder="Search by name or type..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                    />
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {deleteError && (
                  <div className="text-sm text-red-600 bg-red-50 p-2 rounded mb-4">
                    {deleteError}
                  </div>
                )}
                {loading ? (
                  <div className="py-12">
                    <Loading message="Loading documents..." />
                  </div>
                ) : filteredDocuments.length === 0 ? (
                  <EmptyState
                    title="No Documents Found"
                    description={searchQuery ? 'Try a different search term' : 'Upload your first document to get started'}
                    actionLabel="Upload Document"
                    onAction={() => fileInputRef.current?.click()}
                  />
                ) : (
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>File Name</TableHead>
                          <TableHead>Type</TableHead>
                          <TableHead>Size</TableHead>
                          <TableHead>Upload Time</TableHead>
                          <TableHead>Source</TableHead>
                          <TableHead>Status</TableHead>
                          <TableHead className="text-right">Actions</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {filteredDocuments.map((document) => (
                          <TableRow key={document.id}>
                            <TableCell className="font-medium">
                              <div className="flex items-center space-x-2">
                                <div className="w-8 h-8 flex items-center justify-center bg-blue-100 rounded">
                                  <span className="text-blue-600 font-bold">
                                    {document.type.charAt(0)}
                                  </span>
                                </div>
                                <span>{document.name}</span>
                              </div>
                            </TableCell>
                            <TableCell>{document.type}</TableCell>
                            <TableCell>{document.size}</TableCell>
                            <TableCell>
                              {document.uploadedAt.toLocaleDateString()}
                            </TableCell>
                            <TableCell>
                              <div className="space-y-1">
                                <Badge
                                  variant={
                                    document.source === 'knowledge_base'
                                      ? 'secondary'
                                      : 'outline'
                                  }
                                >
                                  {document.source === 'knowledge_base' ? 'Knowledge Base' : 'Uploaded'}
                                </Badge>
                                {document.source === 'knowledge_base' && document.chunkCount ? (
                                  <div className="text-[11px] text-gray-500">
                                    {document.chunkCount} chunks
                                  </div>
                                ) : null}
                              </div>
                            </TableCell>
                            <TableCell>
                              {getStatusBadge(document.status)}
                            </TableCell>
                            <TableCell className="text-right">
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => handleDelete(document.id)}
                                className="text-red-600 hover:text-red-700 hover:bg-red-50"
                              >
                                Delete
                              </Button>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Document statistics */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
              <Card>
                <CardContent className="pt-6">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-gray-900">
                      {documents.length}
                    </div>
                    <div className="text-sm text-gray-600">Total Documents</div>
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-6">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-green-600">
                      {documents.filter(d => d.status === 'processed').length}
                    </div>
                    <div className="text-sm text-gray-600">Processed</div>
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-6">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-blue-600">
                      {formatFileSize(
                        documents.reduce((total, doc) => {
                          const size = parseFloat(doc.size)
                          const unit = doc.size.split(' ')[1]
                          let bytes = size
                          if (unit === 'KB') bytes = size * 1024
                          if (unit === 'MB') bytes = size * 1024 * 1024
                          if (unit === 'GB') bytes = size * 1024 * 1024 * 1024
                          return total + bytes
                        }, 0)
                      )}
                    </div>
                    <div className="text-sm text-gray-600">Total Storage</div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
