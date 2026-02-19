'use client'

import { useState, useEffect, useRef } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { realApiService } from '@/lib/real-api-client'
import type { RealDocumentUploadResponse } from '@/lib/real-api-client'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { FileUpload } from '@/components/ui/files/file-upload'
import { FileList } from '@/components/ui/files/file-list'
import { Loading } from '@/components/ui/feedback/loading'
import { ErrorDisplay } from '@/components/ui/feedback/error-display'
import { EmptyState } from '@/components/ui/feedback/empty-state'

interface Document {
  id: string
  name: string
  type: string
  size: string
  uploadedAt: Date
  status: 'processed' | 'processing' | 'error'
}

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<Document[]>([])
  const [realDocuments, setRealDocuments] = useState<RealDocumentUploadResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [apiStatus, setApiStatus] = useState<'checking' | 'connected' | 'disconnected'>('checking')
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)
  const { user } = useAuth()

  // 加载文档列表
  useEffect(() => {
    loadDocuments()
    checkApiHealth()
  }, [])

  const checkApiHealth = async () => {
    try {
      const health = await realApiService.checkHealth()
      setApiStatus(health.status === 'ok' ? 'connected' : 'disconnected')
    } catch (error) {
      setApiStatus('disconnected')
    }
  }

  const loadDocuments = async () => {
    setLoading(true)
    try {
      // 尝试从真实API加载文档
      const realDocs = await realApiService.getDocuments()
      setRealDocuments(realDocs)
      
      // 转换为前端格式
      const formattedDocs: Document[] = realDocs.map(doc => ({
        id: doc.id,
        name: doc.filename,
        type: getFileType(doc.filename),
        size: formatFileSize(doc.size),
        uploadedAt: new Date(doc.upload_time),
        status: doc.status as 'processed' | 'processing' | 'error'
      }))
      
      setDocuments(formattedDocs)
      
      // 如果没有真实文档，使用模拟数据
      if (formattedDocs.length === 0) {
        setDocuments(getMockDocuments())
      }
    } catch (error) {
      console.error('加载文档失败:', error)
      // 使用模拟数据作为fallback
      setDocuments(getMockDocuments())
    } finally {
      setLoading(false)
    }
  }

  const getMockDocuments = (): Document[] => [
    {
      id: '1',
      name: '建筑成本估算指南.pdf',
      type: 'PDF',
      size: '2.4 MB',
      uploadedAt: new Date('2026-02-13'),
      status: 'processed'
    },
    {
      id: '2',
      name: '项目风险评估报告.docx',
      type: 'Word',
      size: '1.8 MB',
      uploadedAt: new Date('2026-02-12'),
      status: 'processed'
    },
    {
      id: '3',
      name: '施工安全规范.pdf',
      type: 'PDF',
      size: '3.2 MB',
      uploadedAt: new Date('2026-02-11'),
      status: 'processing'
    },
    {
      id: '4',
      name: '材料成本数据.xlsx',
      type: 'Excel',
      size: '4.1 MB',
      uploadedAt: new Date('2026-02-10'),
      status: 'error'
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
      // 模拟上传进度
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval)
            return prev
          }
          return prev + 10
        })
      }, 200)

      // 上传每个文件
      for (const file of selectedFiles) {
        try {
          if (apiStatus === 'connected') {
            // 使用真实API上传
            await realApiService.uploadDocument(file, {
              title: file.name,
              description: `Uploaded by ${user?.name || 'user'}`,
              tags: ['uploaded', getFileType(file.name).toLowerCase()]
            })
          } else {
            // 模拟上传
            await new Promise(resolve => setTimeout(resolve, 1000))
          }
        } catch (error) {
          console.error(`上传文件 ${file.name} 失败:`, error)
        }
      }

      clearInterval(progressInterval)
      setUploadProgress(100)

      // 上传完成，重新加载文档列表
      setTimeout(() => {
        setUploading(false)
        setUploadProgress(0)
        setSelectedFiles([])
        loadDocuments()
        
        // 重置文件输入
        if (fileInputRef.current) {
          fileInputRef.current.value = ''
        }
      }, 500)

    } catch (error) {
      console.error('上传失败:', error)
      setUploading(false)
      setUploadProgress(0)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('确定要删除这个文档吗？')) return

    try {
      // 这里应该调用删除API
      // await realApiService.deleteDocument(id)
      
      // 暂时从前端状态中移除
      setDocuments(prev => prev.filter(doc => doc.id !== id))
      setRealDocuments(prev => prev.filter(doc => doc.id !== id))
    } catch (error) {
      console.error('删除文档失败:', error)
    }
  }

  const handleDownload = (id: string, filename: string) => {
    // 这里应该调用下载API
    // 暂时使用模拟下载
    alert(`开始下载: ${filename}`)
  }

  const filteredDocuments = documents.filter(doc =>
    doc.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    doc.type.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const getStatusBadge = (status: Document['status']) => {
    switch (status) {
      case 'processed':
        return <Badge variant="success">已处理</Badge>
      case 'processing':
        return <Badge variant="warning">处理中</Badge>
      case 'error':
        return <Badge variant="destructive">错误</Badge>
      default:
        return <Badge variant="secondary">未知</Badge>
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* 页面标题和状态 */}
        <div className="mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">文档管理</h1>
              <p className="text-gray-600 mt-2">
                上传、管理和处理建筑项目文档
              </p>
            </div>
            <div className="flex items-center space-x-2">
              <div className={`w-2 h-2 rounded-full ${
                apiStatus === 'connected' ? 'bg-green-500' :
                apiStatus === 'disconnected' ? 'bg-red-500' : 'bg-yellow-500'
              }`}></div>
              <span className="text-sm text-gray-600">
                {apiStatus === 'connected' ? 'API已连接' :
                 apiStatus === 'disconnected' ? 'API未连接（使用模拟数据）' : '检查API状态...'}
              </span>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* 左侧：上传区域 */}
          <div className="lg:col-span-1">
            <Card>
              <CardHeader>
                <CardTitle>上传文档</CardTitle>
                <CardDescription>
                  支持PDF、Word、Excel、图像等格式
                </CardDescription>
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
                      <div className="text-sm font-medium">已选择 {selectedFiles.length} 个文件:</div>
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
                        <span>上传进度</span>
                        <span>{uploadProgress}%</span>
                      </div>
                      <Progress value={uploadProgress} />
                    </div>
                  )}

                  <Button
                    onClick={handleUpload}
                    disabled={selectedFiles.length === 0 || uploading}
                    className="w-full"
                  >
                    {uploading ? '上传中...' : '开始上传'}
                  </Button>

                  <div className="text-xs text-gray-500">
                    <p>• 最大文件大小: 50MB</p>
                    <p>• 支持格式: PDF, Word, Excel, Text, Images</p>
                    <p>• 上传后文档将自动处理和分析</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* API状态卡片 */}
            <Card className="mt-6">
              <CardHeader>
                <CardTitle>API状态</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm">后端连接</span>
                    <Badge variant={apiStatus === 'connected' ? 'success' : 'destructive'}>
                      {apiStatus === 'connected' ? '正常' : '断开'}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">文档总数</span>
                    <span className="font-medium">{realDocuments.length} 个</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">已处理</span>
                    <span className="font-medium">
                      {realDocuments.filter(d => d.status === 'completed').length} 个
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* 右侧：文档列表 */}
          <div className="lg:col-span-2">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>文档列表</CardTitle>
                    <CardDescription>
                      所有已上传的文档，支持搜索和筛选
                    </CardDescription>
                  </div>
                  <div className="w-64">
                    <Input
                      placeholder="搜索文档名称或类型..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                    />
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <div className="py-12">
                    <Loading message="加载文档中..." />
                  </div>
                ) : filteredDocuments.length === 0 ? (
                  <EmptyState
                    title="没有找到文档"
                    description={searchQuery ? '尝试其他搜索词' : '上传您的第一个文档开始使用'}
                    actionLabel="上传文档"
                    onAction={() => fileInputRef.current?.click()}
                  />
                ) : (
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>文档名称</TableHead>
                          <TableHead>类型</TableHead>
                          <TableHead>大小</TableHead>
                          <TableHead>上传时间</TableHead>
                          <TableHead>状态</TableHead>
                          <TableHead className="text-right">操作</TableHead>
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
                              {getStatusBadge(document.status)}
                            </TableCell>
                            <TableCell className="text-right">
                              <div className="flex justify-end space-x-2">
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => handleDownload(document.id, document.name)}
                                >
                                  下载
                                </Button>
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => handleDelete(document.id)}
                                  className="text-red-600 hover:text-red-700 hover:bg-red-50"
                                >
                                  删除
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

            {/* 文档统计 */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
              <Card>
                <CardContent className="pt-6">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-gray-900">
                      {documents.length}
                    </div>
                    <div className="text-sm text-gray-600">总文档数</div>
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-6">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-green-600">
                      {documents.filter(d => d.status === 'processed').length}
                    </div>
                    <div className="text-sm text-gray-600">已处理</div>
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
                    <div className="text-sm text-gray-600">总存储空间</div>
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