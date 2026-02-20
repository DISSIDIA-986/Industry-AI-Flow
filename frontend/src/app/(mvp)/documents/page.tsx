'use client'

import { useState } from 'react'

interface Document {
  id: string
  name: string
  type: string
  size: string
  uploadedAt: Date
  status: 'processed' | 'processing' | 'error'
}

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<Document[]>([
    {
      id: '1',
      name: 'Construction Cost Estimating Guide.pdf',
      type: 'PDF',
      size: '2.4 MB',
      uploadedAt: new Date('2026-02-13'),
      status: 'processed'
    },
    {
      id: '2',
      name: 'Project Risk Assessment Report.docx',
      type: 'Word',
      size: '1.8 MB',
      uploadedAt: new Date('2026-02-12'),
      status: 'processed'
    },
    {
      id: '3',
      name: 'construction schedule.xlsx',
      type: 'Excel',
      size: '3.2 MB',
      uploadedAt: new Date('2026-02-11'),
      status: 'processed'
    },
    {
      id: '4',
      name: 'Material cost data.csv',
      type: 'CSV',
      size: '850 KB',
      uploadedAt: new Date('2026-02-10'),
      status: 'processing'
    }
  ])
  
  const [uploading, setUploading] = useState(false)
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])
    setSelectedFiles(files)
  }

  const handleUpload = async () => {
    if (selectedFiles.length === 0) return

    setUploading(true)
    
    try {
      // useAPIClient upload documents
      const { documentApi } = await import('@/lib/api-client')
      const response = await documentApi.uploadDocuments(selectedFiles)
      
      // Add new document to list
      const newDocuments: Document[] = response.documents.map((doc: {
        id: string
        name: string
        type: string
        size: string
        uploadedAt: string
        status: Document['status']
      }) => ({
        id: doc.id,
        name: doc.name,
        type: doc.type,
        size: doc.size,
        uploadedAt: new Date(doc.uploadedAt),
        status: doc.status
      }))
      
      setDocuments(prev => [...newDocuments, ...prev])
      setSelectedFiles([])
      
      // Clear file input
      const fileInput = document.getElementById('file-upload') as HTMLInputElement
      if (fileInput) fileInput.value = ''
      
      // Simulate document processing status updates
      setTimeout(() => {
        setDocuments(prev => prev.map(doc => 
          newDocuments.some(newDoc => newDoc.id === doc.id) 
            ? { ...doc, status: 'processed' as const }
            : doc
        ))
      }, 3000)
      
    } catch (error) {
      console.error('Upload error:', error)
      alert('File upload failed, please try again')
    } finally {
      setUploading(false)
    }
  }

  const handleDelete = (id: string) => {
    if (confirm('Are you sure you want to delete this document?')) {
      setDocuments(prev => prev.filter(doc => doc.id !== id))
    }
  }

  const handlePreview = (document: Document) => {
    alert(`Preview document: ${document.name}\n\ntype: ${document.type}\nsize: ${document.size}\nUpload time: ${document.uploadedAt.toLocaleDateString()}`)
  }

  const getStatusColor = (status: Document['status']) => {
    switch (status) {
      case 'processed': return 'bg-green-100 text-green-800'
      case 'processing': return 'bg-blue-100 text-blue-800'
      case 'error': return 'bg-red-100 text-red-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const getStatusText = (status: Document['status']) => {
    switch (status) {
      case 'processed': return 'Processed'
      case 'processing': return 'Processing'
      case 'error': return 'Processing failed'
      default: return 'unknown status'
    }
  }

  return (
    <div className="max-w-6xl mx-auto p-4 md:p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Document management</h1>
        <p className="text-gray-600 mt-2">
          Upload and manage your project documents. Supports PDF, Word, Excel, and CSV formats.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Upload area */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h3 className="font-medium text-gray-900 mb-4">Upload documents</h3>
            
            <div className="space-y-4">
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-blue-500 transition">
                <input
                  id="file-upload"
                  type="file"
                  multiple
                  onChange={handleFileSelect}
                  className="hidden"
                  accept=".pdf,.doc,.docx,.xls,.xlsx,.csv,.txt"
                />
                <label htmlFor="file-upload" className="cursor-pointer">
                  <div className="mx-auto w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mb-3">
                    <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                  </div>
                  <div className="text-gray-700">
                    Click to select file or drag and drop here
                  </div>
                  <div className="text-sm text-gray-500 mt-2">
                    support PDF, Word, Excel, CSV, TXT
                  </div>
                </label>
              </div>

              {selectedFiles.length > 0 && (
                <div className="bg-gray-50 rounded-lg p-4">
                  <div className="text-sm font-medium text-gray-900 mb-2">
                    Selected {selectedFiles.length} files
                  </div>
                  <div className="space-y-2 max-h-40 overflow-y-auto">
                    {selectedFiles.map((file, index) => (
                      <div key={index} className="flex items-center justify-between text-sm">
                        <div className="truncate text-gray-700">{file.name}</div>
                        <div className="text-gray-500">
                          {(file.size / 1024 / 1024).toFixed(1)} MB
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <button
                onClick={handleUpload}
                disabled={selectedFiles.length === 0 || uploading}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white py-3 px-4 rounded-lg font-medium transition disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {uploading ? 'Uploading...' : 'Start uploading'}
              </button>
            </div>

            {/* Instructions for use */}
            <div className="mt-6 pt-6 border-t border-gray-200">
              <h4 className="font-medium text-gray-900 mb-2">Instructions for use</h4>
              <ul className="space-y-1 text-sm text-gray-600">
                <li>• Maximum support for a single file 50MB</li>
                <li>• Support batch upload of multiple files</li>
                <li>• Documents are automatically processed and analyzed after uploading</li>
                <li>• After the processing is completed, the document content can be queried in the chat</li>
              </ul>
            </div>
          </div>
        </div>

        {/* Document list */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-xl shadow-sm border border-gray-200">
            <div className="p-4 border-b border-gray-200">
              <div className="flex justify-between items-center">
                <h3 className="font-medium text-gray-900">Document list</h3>
                <div className="text-sm text-gray-500">
                  common {documents.length} documents
                </div>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-gray-50">
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      file name
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      type
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      size
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Upload time
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      state
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      operate
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {documents.map((document) => (
                    <tr key={document.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4">
                        <div className="flex items-center">
                          <div className="w-8 h-8 bg-blue-100 rounded flex items-center justify-center mr-3">
                            <span className="text-blue-600 font-medium text-sm">
                              {document.type.charAt(0)}
                            </span>
                          </div>
                          <div className="text-sm font-medium text-gray-900">
                            {document.name}
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500">
                        {document.type}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500">
                        {document.size}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500">
                        {document.uploadedAt.toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(document.status)}`}>
                          {getStatusText(document.status)}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm font-medium">
                        <div className="flex space-x-2">
                          <button
                            onClick={() => handlePreview(document)}
                            className="text-blue-600 hover:text-blue-900"
                          >
                            Preview
                          </button>
                          <button
                            onClick={() => handleDelete(document.id)}
                            className="text-red-600 hover:text-red-900"
                          >
                            delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {documents.length === 0 && (
              <div className="text-center py-12">
                <div className="text-gray-400 mb-2">No document yet</div>
                <div className="text-sm text-gray-500">
                  Upload your first document to get started
                </div>
              </div>
            )}
          </div>

          {/* Statistics */}
          <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
              <div className="text-sm text-gray-500 mb-1">Total number of documents</div>
              <div className="text-2xl font-bold text-gray-900">{documents.length}</div>
            </div>
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
              <div className="text-sm text-gray-500 mb-1">Processed</div>
              <div className="text-2xl font-bold text-green-600">
                {documents.filter(d => d.status === 'processed').length}
              </div>
            </div>
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
              <div className="text-sm text-gray-500 mb-1">total size</div>
              <div className="text-2xl font-bold text-blue-600">
                {documents.reduce((total, doc) => {
                  const size = parseFloat(doc.size)
                  return total + size
                }, 0).toFixed(1)} MB
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
