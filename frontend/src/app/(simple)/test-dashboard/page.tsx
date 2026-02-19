'use client'

export default function TestDashboardPage() {
  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">数据可视化测试页面</h1>
        
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">图表组件测试</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="p-4 bg-blue-50 rounded-lg">
              <div className="text-blue-600 font-medium mb-2">线图组件</div>
              <div className="text-sm text-gray-600">显示时间序列数据</div>
            </div>
            
            <div className="p-4 bg-green-50 rounded-lg">
              <div className="text-green-600 font-medium mb-2">柱状图组件</div>
              <div className="text-sm text-gray-600">显示分类数据对比</div>
            </div>
            
            <div className="p-4 bg-purple-50 rounded-lg">
              <div className="text-purple-600 font-medium mb-2">饼图组件</div>
              <div className="text-sm text-gray-600">显示比例分布</div>
            </div>
            
            <div className="p-4 bg-orange-50 rounded-lg">
              <div className="text-orange-600 font-medium mb-2">雷达图组件</div>
              <div className="text-sm text-gray-600">显示多维评估</div>
            </div>
          </div>
        </div>
        
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">系统状态</h2>
          <div className="space-y-4">
            <div className="flex items-center">
              <div className="w-3 h-3 bg-green-500 rounded-full mr-3"></div>
              <div className="text-gray-900">前端服务: 运行正常</div>
            </div>
            <div className="flex items-center">
              <div className="w-3 h-3 bg-green-500 rounded-full mr-3"></div>
              <div className="text-gray-900">后端API: 运行正常</div>
            </div>
            <div className="flex items-center">
              <div className="w-3 h-3 bg-green-500 rounded-full mr-3"></div>
              <div className="text-gray-900">数据可视化: 已启用</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}