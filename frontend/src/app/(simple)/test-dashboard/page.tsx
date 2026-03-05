'use client'

export default function TestDashboardPage() {
  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">Data visualization test page</h1>
        
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Chart component testing</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="p-4 bg-blue-50 rounded-lg">
              <div className="text-blue-600 font-medium mb-2">Line chart component</div>
              <div className="text-sm text-gray-600">Display time series data</div>
            </div>
            
            <div className="p-4 bg-green-50 rounded-lg">
              <div className="text-green-600 font-medium mb-2">Bar chart component</div>
              <div className="text-sm text-gray-600">Show categorical data comparison</div>
            </div>
            
            <div className="p-4 bg-purple-50 rounded-lg">
              <div className="text-purple-600 font-medium mb-2">Pie chart component</div>
              <div className="text-sm text-gray-600">Show proportional distribution</div>
            </div>
            
            <div className="p-4 bg-orange-50 rounded-lg">
              <div className="text-orange-600 font-medium mb-2">Radar chart component</div>
              <div className="text-sm text-gray-600">Show multidimensional assessment</div>
            </div>
          </div>
        </div>
        
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">System status</h2>
          <div className="space-y-4">
            <div className="flex items-center">
              <div className="w-3 h-3 bg-green-500 rounded-full mr-3"></div>
              <div className="text-gray-900">Front-end services: Running normally</div>
            </div>
            <div className="flex items-center">
              <div className="w-3 h-3 bg-green-500 rounded-full mr-3"></div>
              <div className="text-gray-900">Backend API: Running normally</div>
            </div>
            <div className="flex items-center">
              <div className="w-3 h-3 bg-green-500 rounded-full mr-3"></div>
              <div className="text-gray-900">Data visualization: Enabled</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}