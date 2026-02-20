'use client'

import { useState } from 'react'
import {
  // 表单组件
  Form, FormGroup, Input, TextArea, Select, Checkbox, RadioGroup, Button,
  // 表格组件
  Table, TableHead, TableHeader, TableBody, TableRow, TableCell, Pagination,
  // 卡片组件
  Card, CardHeader, CardTitle, CardContent, StatCard, InfoCard,
  // 模态框组件
  Modal, ConfirmModal, LoadingModal,
  // 反馈组件
  Loading, ErrorDisplay, EmptyState, Skeleton, ProgressBar,
  // 文件组件
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
    { value: 'general', label: '一般咨询' },
    { value: 'technical', label: '技术支持' },
    { value: 'billing', label: '账单问题' },
    { value: 'feedback', label: '反馈建议' }
  ]

  const priorities = [
    { value: 'low', label: '低优先级' },
    { value: 'medium', label: '中优先级' },
    { value: 'high', label: '高优先级' }
  ]

  const tableData = [
    { id: 1, name: '项目A', status: '进行中', progress: 75, budget: '$1,200,000' },
    { id: 2, name: '项目B', status: '已完成', progress: 100, budget: '$850,000' },
    { id: 3, name: '项目C', status: '待开始', progress: 0, budget: '$2,100,000' },
    { id: 4, name: '项目D', status: '暂停', progress: 30, budget: '$1,500,000' }
  ]

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    console.log('表单数据:', formData)
    setShowLoading(true)
    
    setTimeout(() => {
      setShowLoading(false)
      alert('表单提交成功！')
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
        <h1 className="text-3xl font-bold text-gray-900">组件演示</h1>
        <p className="text-gray-600 mt-2">
          展示所有可用的UI组件及其用法
        </p>
      </div>

      <div className="space-y-8">
        {/* 表单组件 */}
        <section>
          <h2 className="text-2xl font-bold text-gray-900 mb-6">表单组件</h2>
          <Card>
            <CardHeader>
              <CardTitle>联系表单</CardTitle>
            </CardHeader>
            <CardContent>
              <Form onSubmit={handleSubmit}>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <FormGroup label="姓名" required>
                    <Input
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      placeholder="请输入您的姓名"
                    />
                  </FormGroup>

                  <FormGroup label="邮箱" required>
                    <Input
                      type="email"
                      value={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      placeholder="example@email.com"
                    />
                  </FormGroup>

                  <FormGroup label="问题类别">
                    <Select
                      value={formData.category}
                      onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                      options={categories}
                    />
                  </FormGroup>

                  <FormGroup label="优先级">
                    <RadioGroup
                      options={priorities}
                      value={formData.priority}
                      onChange={(value) => setFormData({ ...formData, priority: value })}
                    />
                  </FormGroup>

                  <FormGroup className="md:col-span-2" label="详细描述">
                    <TextArea
                      value={formData.message}
                      onChange={(e) => setFormData({ ...formData, message: e.target.value })}
                      rows={4}
                      placeholder="请详细描述您的问题..."
                    />
                  </FormGroup>

                  <div className="md:col-span-2">
                    <Checkbox
                      label="订阅产品更新和通知"
                      checked={formData.subscribe}
                      onChange={(e) => setFormData({ ...formData, subscribe: e.target.checked })}
                    />
                  </div>
                </div>

                <div className="flex space-x-4 mt-6">
                  <Button type="submit">提交表单</Button>
                  <Button variant="outline" onClick={() => setFormData({
                    name: '',
                    email: '',
                    message: '',
                    category: '',
                    subscribe: false,
                    priority: 'medium'
                  })}>
                    重置
                  </Button>
                </div>
              </Form>
            </CardContent>
          </Card>
        </section>

        {/* 卡片组件 */}
        <section>
          <h2 className="text-2xl font-bold text-gray-900 mb-6">卡片组件</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <StatCard
              title="总项目数"
              value={42}
              change="+12%"
              trend="up"
            />
            <StatCard
              title="活跃项目"
              value={18}
              change="+5%"
              trend="up"
            />
            <StatCard
              title="风险评分"
              value="65/100"
              change="-8%"
              trend="down"
            />
            <StatCard
              title="预算利用率"
              value="78%"
              change="+3.2%"
              trend="up"
            />
          </div>

          <div className="mt-6">
            <InfoCard
              title="项目详情"
              description="当前项目的详细信息和状态"
              actions={
                <Button size="sm">编辑</Button>
              }
            >
              <div className="space-y-4">
                <div className="flex justify-between">
                  <span className="text-gray-600">项目名称</span>
                  <span className="font-medium">Industry AI Flow</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">状态</span>
                  <span className="px-2 py-1 bg-green-100 text-green-800 rounded-full text-sm">
                    进行中
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">进度</span>
                  <span className="font-medium">85%</span>
                </div>
              </div>
            </InfoCard>
          </div>
        </section>

        {/* 表格组件 */}
        <section>
          <h2 className="text-2xl font-bold text-gray-900 mb-6">表格组件</h2>
          <Card>
            <CardHeader>
              <CardTitle>项目列表</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableHeader>项目名称</TableHeader>
                    <TableHeader>状态</TableHeader>
                    <TableHeader>进度</TableHeader>
                    <TableHeader>预算</TableHeader>
                    <TableHeader align="right">操作</TableHeader>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {tableData.map((row) => (
                    <TableRow key={row.id}>
                      <TableCell className="font-medium">{row.name}</TableCell>
                      <TableCell>
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                          row.status === '进行中' ? 'bg-blue-100 text-blue-800' :
                          row.status === '已完成' ? 'bg-green-100 text-green-800' :
                          row.status === '待开始' ? 'bg-yellow-100 text-yellow-800' :
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
                          <Button size="sm" variant="outline">查看</Button>
                          <Button size="sm">编辑</Button>
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

        {/* 文件上传组件 */}
        <section>
          <h2 className="text-2xl font-bold text-gray-900 mb-6">文件上传组件</h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>文件上传</CardTitle>
              </CardHeader>
              <CardContent>
                <FileUpload
                  onFileSelect={handleFileSelect}
                  accept=".pdf,.doc,.docx,.xlsx,.xls,.jpg,.png"
                  maxSize={10}
                  label="上传文件"
                  helpText="支持文档和图片格式，最大10MB"
                />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>已上传文件</CardTitle>
              </CardHeader>
              <CardContent>
                {uploadedFiles.length === 0 ? (
                  <EmptyState
                    title="暂无文件"
                    description="上传文件后，它们将显示在这里"
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

        {/* 反馈组件 */}
        <section>
          <h2 className="text-2xl font-bold text-gray-900 mb-6">反馈组件</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>加载状态</CardTitle>
              </CardHeader>
              <CardContent>
                <Loading text="加载中..." />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>错误显示</CardTitle>
              </CardHeader>
              <CardContent>
                <ErrorDisplay
                  title="加载失败"
                  message="无法加载数据，请检查网络连接后重试"
                  onRetry={() => alert('重试中...')}
                />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>进度条</CardTitle>
              </CardHeader>
              <CardContent>
                <ProgressBar
                  value={65}
                  label="项目进度"
                  showPercentage
                />
              </CardContent>
            </Card>
          </div>

          <div className="mt-6">
            <Card>
              <CardHeader>
                <CardTitle>骨架屏</CardTitle>
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

        {/* 模态框组件 */}
        <section>
          <h2 className="text-2xl font-bold text-gray-900 mb-6">模态框组件</h2>
          <div className="flex space-x-4">
            <Button onClick={() => setShowModal(true)}>
              打开模态框
            </Button>
            <Button variant="danger" onClick={() => setShowConfirm(true)}>
              删除确认
            </Button>
            <Button variant="secondary" onClick={() => setShowLoading(true)}>
              显示加载
            </Button>
          </div>
        </section>
      </div>

      {/* 模态框 */}
      <Modal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        title="示例模态框"
        size="md"
      >
        <div className="space-y-4">
          <p className="text-gray-600">
            这是一个模态框示例。您可以在这里放置任何内容，如表单、信息或操作按钮。
          </p>
          <div className="flex justify-end space-x-3">
            <Button variant="outline" onClick={() => setShowModal(false)}>
              取消
            </Button>
            <Button onClick={() => setShowModal(false)}>
              确认
            </Button>
          </div>
        </div>
      </Modal>

      {/* 确认模态框 */}
      <ConfirmModal
        isOpen={showConfirm}
        onClose={() => setShowConfirm(false)}
        onConfirm={() => {
          alert('删除操作已确认')
          setShowConfirm(false)
        }}
        title="确认删除"
        message="确定要删除此项目吗？此操作不可恢复。"
        confirmText="删除"
        cancelText="取消"
        variant="danger"
      />

      {/* 加载模态框 */}
      <LoadingModal
        isOpen={showLoading}
        title="处理中"
        message="请稍候，正在处理您的请求..."
      />
    </div>
  )
}
