'use client'

import { useState, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { realApiService } from '@/lib/real-api-client'
import type { RealDocumentListResponse } from '@/lib/real-api-client'
import { Card, CardContent, CardHeader, CardTitle, StatCard } from '@/components/cards'
import { Button } from '@/components/forms'
import { Input } from '@/components/forms'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/tables'
import { FileUpload } from '@/components/files'
import { Loading, EmptyState } from '@/components/feedback'

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

export default function DocumentsIntegratedPage() {
  const [documents, setDocuments] = useState<Document[]>([])
  const [realDocuments, setRealDocuments] = useState<RealDocumentListResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [apiStatus, setApiStatus] = useState<'checking' | 'connected' | 'disconnected'>('checking')
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
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
        setRealDocuments([])
        setDocuments(ALLOW_DOCUMENTS_MOCK_FALLBACK ? getMockDocuments() : [])
        return
      }

      // try from realityAPILoad document
      const realDocs = await realApiService.getDocuments()
      setRealDocuments(realDocs)
      
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
      console.error('Failed to load document:', error)
      setApiStatus('disconnected')
      if (ALLOW_DOCUMENTS_MOCK_FALLBACK) {
        setDocuments(getMockDocuments())
      } else {
        setDocuments([])
      }
      setRealDocuments([])
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
      name: 'Construction safety regulations.pdf',
      type: 'PDF',
      size: '3.2 MB',
      uploadedAt: new Date('2026-02-11'),
      status: 'processing',
      source: 'uploaded',
    },
    {
      id: '4',
      name: 'Material cost data.xlsx',
      type: 'Excel',
      size: '4.1 MB',
      uploadedAt: new Date('2026-02-10'),
      status: 'error',
      source: 'uploaded',
    }
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

      // Upload each file
      for (const file of selectedFiles) {
        try {
          if (apiStatus === 'connected') {
            // use realAPIupload
            await realApiService.uploadDocument(file, {
              title: file.name,
              description: `Uploaded by ${user?.name || 'user'}`,
              tags: ['uploaded', getFileType(file.name).toLowerCase()]
            })
          } else {
            // Simulate upload
            await new Promise(resolve => setTimeout(resolve, 1000))
          }
        } catch (error) {
          console.error(`Upload files ${file.name} fail:`, error)
        }
      }

      clearInterval(progressInterval)
      setUploadProgress(100)

      // Upload completed, reload the document list
      setTimeout(() => {
        setUploading(false)
        setUploadProgress(0)
        setSelectedFiles([])
        loadDocuments()
      }, 500)

    } catch (error) {
      console.error('Upload failed:', error)
      setUploading(false)
      setUploadProgress(0)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this document?')) return

    try {
      // Delete should be called hereAPI
      // await realApiService.deleteDocument(id)
      
      // Temporarily removed from frontend status
      setDocuments(prev => prev.filter(doc => doc.id !== id))
      setRealDocuments(prev => prev.filter(doc => doc.id !== id))
    } catch (error) {
      console.error('Failed to delete document:', error)
    }
  }

  const handleDownload = (id: string, filename: string) => {
    // Download should be called hereAPI
    // Temporarily use simulated downloads
    alert(`Start downloading: ${filename}`)
  }

  const filteredDocuments = documents.filter(doc =>
    doc.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    doc.type.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const getStatusColor = (status: Document['status']) => {
    switch (status) {
      case 'processed':
        return 'bg-green-100 text-green-800'
      case 'processing':
        return 'bg-yellow-100 text-yellow-800'
      case 'error':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Page title and status */}
        <div className="mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Document management</h1>
              <p className="text-gray-600 mt-2">
                Upload, manage and process construction project documents
              </p>
            </div>
            <div className="flex items-center space-x-2">
              <div className={`w-2 h-2 rounded-full ${
                apiStatus === 'connected' ? 'bg-green-500' :
                apiStatus === 'disconnected' ? 'bg-red-500' : 'bg-yellow-500'
              }`}></div>
              <span className="text-sm text-gray-600">
                {apiStatus === 'connected' ? 'API Connected' :
                 apiStatus === 'disconnected' ? 'API Disconnected' : 'Checking API status...'}
              </span>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: Upload area */}
          <div className="lg:col-span-1">
            <Card>
              <CardHeader>
                <CardTitle>Upload documents</CardTitle>
                <p className="text-sm text-gray-600 mt-1">
                  Supports PDF, Word, Excel, Image, and other formats.
                </p>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <FileUpload
                    onFilesSelected={handleFileSelect}
                    accept=".pdf,.doc,.docx,.xls,.xlsx,.txt,.jpg,.jpeg,.png"
                    maxSize={50 * 1024 * 1024} // 50MB
                    multiple
                  />
                  
                  {selectedFiles.length > 0 && (
                    <div className="space-y-2">
                      <div className="text-sm font-medium">Selected {selectedFiles.length} files:</div>
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
                        <span>Upload progress</span>
                        <span>{uploadProgress}%</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div 
                          className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                          style={{ width: `${uploadProgress}%` }}
                        ></div>
                      </div>
                    </div>
                  )}

                  <Button
                    onClick={handleUpload}
                    disabled={selectedFiles.length === 0 || uploading}
                    className="w-full"
                  >
                    {uploading ? 'Uploading...' : 'Start uploading'}
                  </Button>

                  <div className="text-xs text-gray-500">
                    <p>• Maximum file size: 50MB</p>
                    <p>• Supported formats: PDF, Word, Excel, Text, Images</p>
                    <p>• Documents will be automatically processed and analyzed after uploading</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* APIstatus card */}
            <Card className="mt-6">
              <CardHeader>
                <CardTitle>API Status</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm">backend connection</span>
                    <span className={`px-2 py-1 rounded text-xs ${
                      apiStatus === 'connected' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                    }`}>
                      {apiStatus === 'connected' ? 'normal' : 'disconnect'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Total number of documents</span>
                    <span className="font-medium">{realDocuments.length} indivual</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Processed</span>
                    <span className="font-medium">
                      {realDocuments.filter(d => d.status === 'completed' || d.status === 'processed').length} indivual
                    </span>
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
                    <CardTitle>Document list</CardTitle>
                    <p className="text-sm text-gray-600 mt-1">
                      All uploaded documents support search and filtering
                    </p>
                  </div>
                  <div className="w-64">
                    <Input
                      placeholder="Search document name or type..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                    />
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <div className="py-12">
                    <Loading message="Loading document..." />
                  </div>
                ) : filteredDocuments.length === 0 ? (
                  <EmptyState
                    title="No document found"
                    description={searchQuery ? 'Try other search terms' : 'Upload your first document to get started'}
                    actionLabel="Upload documents"
                    onAction={() => {/* Trigger file selection */}}
                  />
                ) : (
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>file name</TableHead>
                          <TableHead>type</TableHead>
                          <TableHead>size</TableHead>
                          <TableHead>Upload time</TableHead>
                          <TableHead>source</TableHead>
                          <TableHead>state</TableHead>
                          <TableHead className="text-right">operate</TableHead>
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
                                <span
                                  className={`px-2 py-1 rounded text-xs ${
                                    document.source === 'knowledge_base'
                                      ? 'bg-indigo-100 text-indigo-800'
                                      : 'bg-slate-100 text-slate-700'
                                  }`}
                                >
                                  {document.source === 'knowledge_base' ? 'Knowledge Base' : 'Uploaded'}
                                </span>
                                {document.source === 'knowledge_base' && document.chunkCount ? (
                                  <div className="text-[11px] text-gray-500">
                                    {document.chunkCount} chunks
                                  </div>
                                ) : null}
                              </div>
                            </TableCell>
                            <TableCell>
                              <span className={`px-2 py-1 rounded text-xs ${getStatusColor(document.status)}`}>
                                {document.status === 'processed' ? 'Processed' :
                                 document.status === 'processing' ? 'Processing' : 'Error'}
                              </span>
                            </TableCell>
                            <TableCell className="text-right">
                              <div className="flex justify-end space-x-2">
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => handleDownload(document.id, document.name)}
                                >
                                  download
                                </Button>
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => handleDelete(document.id)}
                                  className="text-red-600 hover:text-red-700 hover:bg-red-50"
                                >
                                  delete
                                </Button>
                              </div>
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
              <StatCard
                title="Total number of documents"
                value={documents.length.toString()}
                description="Uploaded and knowledge base documents"
                trend="up"
              />
              <StatCard
                title="Processed"
                value={documents.filter(d => d.status === 'processed').length.toString()}
                description="Completed documents"
                trend="up"
              />
              <StatCard
                title="total storage space"
                value={formatFileSize(
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
                description="Space occupied by all documents"
                trend="up"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
