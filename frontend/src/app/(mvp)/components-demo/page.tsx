'use client'

import { useState } from 'react'
import {
  // form component
  Form, FormGroup, Input, TextArea, Select, Checkbox, RadioGroup, Button,
  // Table component
  Table, TableHead, TableHeader, TableBody, TableRow, TableCell, Pagination,
  // card component
  Card, CardHeader, CardTitle, CardContent, StatCard, InfoCard,
  // Modal component
  Modal, ConfirmModal, LoadingModal,
  // feedback component
  Loading, ErrorDisplay, EmptyState, Skeleton, ProgressBar,
  // file component
  FileUpload, FileList
} from '@/components'

export default function ComponentsDemoPage() {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    message: '',
    category: '',
    subscribe: false,
    priority: 'medium'
  })

  const [currentPage, setCurrentPage] = useState(1)
  const [showModal, setShowModal] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [showLoading, setShowLoading] = useState(false)
  const [uploadedFiles, setUploadedFiles] = useState<Array<{
    id: string
    name: string
    size: string
    uploadedAt: string
  }>>([])

  const categories = [
    { value: 'general', label: 'General Inquiries' },
    { value: 'technical', label: 'Technical support' },
    { value: 'billing', label: 'Billing Issues' },
    { value: 'feedback', label: 'Feedback and Suggestions' }
  ]

  const priorities = [
    { value: 'low', label: 'low priority' },
    { value: 'medium', label: 'medium priority' },
    { value: 'high', label: 'high priority' }
  ]

  const tableData = [
    { id: 1, name: 'projectA', status: 'in progress', progress: 75, budget: '$1,200,000' },
    { id: 2, name: 'projectB', status: 'Completed', progress: 100, budget: '$850,000' },
    { id: 3, name: 'projectC', status: 'To be started', progress: 0, budget: '$2,100,000' },
    { id: 4, name: 'projectD', status: 'pause', progress: 30, budget: '$1,500,000' }
  ]

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    console.log('Form data:', formData)
    setShowLoading(true)
    
    setTimeout(() => {
      setShowLoading(false)
      alert('The form was submitted successfully!')
    }, 2000)
  }

  const handleFileSelect = (file: File) => {
    const newFile = {
      id: Date.now().toString(),
      name: file.name,
      size: `${(file.size / (1024 * 1024)).toFixed(1)} MB`,
      uploadedAt: new Date().toLocaleString()
    }
    
    setUploadedFiles(prev => [...prev, newFile])
  }

  const handleDeleteFile = (id: string) => {
    setUploadedFiles(prev => prev.filter(file => file.id !== id))
  }

  return (
    <div className="max-w-7xl mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Component demo</h1>
        <p className="text-gray-600 mt-2">
          Show all available UI components and their usage
        </p>
      </div>

      <div className="space-y-8">
        {/* form component */}
        <section>
          <h2 className="text-2xl font-bold text-gray-900 mb-6">form component</h2>
          <Card>
            <CardHeader>
              <CardTitle>Contact form</CardTitle>
            </CardHeader>
            <CardContent>
              <Form onSubmit={handleSubmit}>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <FormGroup label="Name" required>
                    <Input
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      placeholder="Please enter your name"
                    />
                  </FormGroup>

                  <FormGroup label="Mail" required>
                    <Input
                      type="email"
                      value={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      placeholder="example@email.com"
                    />
                  </FormGroup>

                  <FormGroup label="Question Category">
                    <Select
                      value={formData.category}
                      onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                      options={categories}
                    />
                  </FormGroup>

                  <FormGroup label="Priority">
                    <RadioGroup
                      options={priorities}
                      value={formData.priority}
                      onChange={(value) => setFormData({ ...formData, priority: value })}
                    />
                  </FormGroup>

                  <FormGroup className="md:col-span-2" label="Detailed description">
                    <TextArea
                      value={formData.message}
                      onChange={(e) => setFormData({ ...formData, message: e.target.value })}
                      rows={4}
                      placeholder="Please describe your problem in detail..."
                    />
                  </FormGroup>

                  <div className="md:col-span-2">
                    <Checkbox
                      label="Subscribe to product updates and notifications"
                      checked={formData.subscribe}
                      onChange={(e) => setFormData({ ...formData, subscribe: e.target.checked })}
                    />
                  </div>
                </div>

                <div className="flex space-x-4 mt-6">
                  <Button type="submit">Submit form</Button>
                  <Button variant="outline" onClick={() => setFormData({
                    name: '',
                    email: '',
                    message: '',
                    category: '',
                    subscribe: false,
                    priority: 'medium'
                  })}>
                    reset
                  </Button>
                </div>
              </Form>
            </CardContent>
          </Card>
        </section>

        {/* card component */}
        <section>
          <h2 className="text-2xl font-bold text-gray-900 mb-6">card component</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <StatCard
              title="Total number of items"
              value={42}
              change="+12%"
              trend="up"
            />
            <StatCard
              title="Active projects"
              value={18}
              change="+5%"
              trend="up"
            />
            <StatCard
              title="risk score"
              value="65/100"
              change="-8%"
              trend="down"
            />
            <StatCard
              title="budget utilization"
              value="78%"
              change="+3.2%"
              trend="up"
            />
          </div>

          <div className="mt-6">
            <InfoCard
              title="Project details"
              description="Details and status of current projects"
              actions={
                <Button size="sm">edit</Button>
              }
            >
              <div className="space-y-4">
                <div className="flex justify-between">
                  <span className="text-gray-600">Project name</span>
                  <span className="font-medium">Industry AI Flow</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">state</span>
                  <span className="px-2 py-1 bg-green-100 text-green-800 rounded-full text-sm">
                    in progress
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">schedule</span>
                  <span className="font-medium">85%</span>
                </div>
              </div>
            </InfoCard>
          </div>
        </section>

        {/* Table component */}
        <section>
          <h2 className="text-2xl font-bold text-gray-900 mb-6">Table component</h2>
          <Card>
            <CardHeader>
              <CardTitle>Project list</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableHeader>Project name</TableHeader>
                    <TableHeader>state</TableHeader>
                    <TableHeader>schedule</TableHeader>
                    <TableHeader>Budget</TableHeader>
                    <TableHeader align="right">operate</TableHeader>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {tableData.map((row) => (
                    <TableRow key={row.id}>
                      <TableCell className="font-medium">{row.name}</TableCell>
                      <TableCell>
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                          row.status === 'in progress' ? 'bg-blue-100 text-blue-800' :
                          row.status === 'Completed' ? 'bg-green-100 text-green-800' :
                          row.status === 'To be started' ? 'bg-yellow-100 text-yellow-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {row.status}
                        </span>
                      </TableCell>
                      <TableCell>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-blue-600 h-2 rounded-full"
                            style={{ width: `${row.progress}%` }}
                          />
                        </div>
                        <div className="text-xs text-gray-500 mt-1">{row.progress}%</div>
                      </TableCell>
                      <TableCell>{row.budget}</TableCell>
                      <TableCell align="right">
                        <div className="flex justify-end space-x-2">
                          <Button size="sm" variant="outline">Check</Button>
                          <Button size="sm">edit</Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              <div className="mt-6">
                <Pagination
                  currentPage={currentPage}
                  totalPages={5}
                  onPageChange={setCurrentPage}
                />
              </div>
            </CardContent>
          </Card>
        </section>

        {/* File upload component */}
        <section>
          <h2 className="text-2xl font-bold text-gray-900 mb-6">File upload component</h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>File upload</CardTitle>
              </CardHeader>
              <CardContent>
                <FileUpload
                  onFileSelect={handleFileSelect}
                  accept=".pdf,.doc,.docx,.xlsx,.xls,.jpg,.png"
                  maxSize={10}
                  label="Upload files"
                  helpText="Support document and image formats, up to 10MB"
                />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>File uploaded</CardTitle>
              </CardHeader>
              <CardContent>
                {uploadedFiles.length === 0 ? (
                  <EmptyState
                    title="No files yet"
                    description="Once your files are uploaded, they will appear here"
                  />
                ) : (
                  <FileList
                    files={uploadedFiles}
                    onDelete={handleDeleteFile}
                  />
                )}
              </CardContent>
            </Card>
          </div>
        </section>

        {/* feedback component */}
        <section>
          <h2 className="text-2xl font-bold text-gray-900 mb-6">feedback component</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Loading status</CardTitle>
              </CardHeader>
              <CardContent>
                <Loading text="loading..." />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>error display</CardTitle>
              </CardHeader>
              <CardContent>
                <ErrorDisplay
                  title="Loading failed"
                  message="Unable to load data, please check the network connection and try again"
                  onRetry={() => alert('Retrying...')}
                />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>progress bar</CardTitle>
              </CardHeader>
              <CardContent>
                <ProgressBar
                  value={65}
                  label="Project progress"
                  showPercentage
                />
              </CardContent>
            </Card>
          </div>

          <div className="mt-6">
            <Card>
              <CardHeader>
                <CardTitle>skeleton screen</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <Skeleton count={3} height="h-4" />
                  <Skeleton height="h-20" />
                </div>
              </CardContent>
            </Card>
          </div>
        </section>

        {/* Modal component */}
        <section>
          <h2 className="text-2xl font-bold text-gray-900 mb-6">Modal component</h2>
          <div className="flex space-x-4">
            <Button onClick={() => setShowModal(true)}>
              Open modal box
            </Button>
            <Button variant="danger" onClick={() => setShowConfirm(true)}>
              Delete confirmation
            </Button>
            <Button variant="secondary" onClick={() => setShowLoading(true)}>
              show loading
            </Button>
          </div>
        </section>
      </div>

      {/* modal box */}
      <Modal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        title="Example modal box"
        size="md"
      >
        <div className="space-y-4">
          <p className="text-gray-600">
            Here is an example of a modal box. You can place anything here, such as forms, information, or action buttons.
          </p>
          <div className="flex justify-end space-x-3">
            <Button variant="outline" onClick={() => setShowModal(false)}>
              Cancel
            </Button>
            <Button onClick={() => setShowModal(false)}>
              confirm
            </Button>
          </div>
        </div>
      </Modal>

      {/* Confirm modal box */}
      <ConfirmModal
        isOpen={showConfirm}
        onClose={() => setShowConfirm(false)}
        onConfirm={() => {
          alert('Delete operation confirmed')
          setShowConfirm(false)
        }}
        title="Confirm deletion"
        message="Are you sure you want to delete this item? This operation is irreversible."
        confirmText="delete"
        cancelText="Cancel"
        variant="danger"
      />

      {/* Load modal box */}
      <LoadingModal
        isOpen={showLoading}
        title="Processing"
        message="Please wait, your request is being processed..."
      />
    </div>
  )
}
