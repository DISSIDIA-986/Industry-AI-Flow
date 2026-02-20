'use client'

import { useState, useEffect } from 'react'
import { 
  LineChartComponent, BarChartComponent, PieChartComponent, 
  AreaChartComponent, RadarChartComponent,
  MetricCard, DataTable
} from '@/components/charts'
import { dataApi } from '@/lib/data-generator'

export default function DataDashboardPage() {
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState<any>(null)
  const [timeRange, setTimeRange] = useState('monthly')

  useEffect(() => {
    loadData()
  }, [timeRange])

  const loadData = async () => {
    setLoading(true)
    try {
      const allData = await dataApi.getAllData()
      setData(allData)
    } catch (error) {
      console.error('Failed to load data:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading || !data) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-7xl mx-auto">
          <div className="animate-pulse">
            <div className="h-8 bg-gray-200 rounded w-1/4 mb-8"></div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="h-32 bg-gray-200 rounded"></div>
              ))}
            </div>
            <div className="h-96 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Title and time filter */}
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Data analysis dashboard</h1>
          <div className="flex space-x-2">
            <button
              onClick={() => setTimeRange('daily')}
              className={`px-4 py-2 rounded-lg ${timeRange === 'daily' ? 'bg-blue-600 text-white' : 'bg-white text-gray-700 border border-gray-300'}`}
            >
              day
            </button>
            <button
              onClick={() => setTimeRange('weekly')}
              className={`px-4 py-2 rounded-lg ${timeRange === 'weekly' ? 'bg-blue-600 text-white' : 'bg-white text-gray-700 border border-gray-300'}`}
            >
              Weekly
            </button>
            <button
              onClick={() => setTimeRange('monthly')}
              className={`px-4 py-2 rounded-lg ${timeRange === 'monthly' ? 'bg-blue-600 text-white' : 'bg-white text-gray-700 border border-gray-300'}`}
            >
              monthly
            </button>
          </div>
        </div>

        {/* KPI indicator card */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <MetricCard
            title="Total number of items"
            value={data.kpiMetrics.totalProjects}
            change="+12%"
          />
          <MetricCard
            title="Active projects"
            value={data.kpiMetrics.activeProjects}
            change="+5%"
          />
          <MetricCard
            title="budget utilization"
            value={`${data.kpiMetrics.budgetUtilization}%`}
            change="+3.2%"
          />
          <MetricCard
            title="risk score"
            value={`${data.kpiMetrics.riskScore}/100`}
            change="-8%"
          />
        </div>

        {/* First row chart */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* Cost trend chart */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-6">Cost trend analysis</h2>
            <LineChartComponent
              data={data.timeSeries}
              title="monthly cost changes"
              height={300}
            />
          </div>

          {/* Project type distribution */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-6">Project type distribution</h2>
            <PieChartComponent
              data={data.category}
              title="Proportion of project types"
              height={300}
            />
          </div>
        </div>

        {/* Second row of charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* Cost composition analysis */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-6">Cost composition analysis</h2>
            <BarChartComponent
              data={data.costDistribution}
              title="Cost composition ratio"
              height={300}
            />
          </div>

          {/* Risk Assessment Radar Chart */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-6">risk assessment</h2>
            <RadarChartComponent
              data={data.riskData}
              title="Risk dimension assessment"
              height={300}
            />
          </div>
        </div>

        {/* Real-time monitoring */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold text-gray-900">Real-time system monitoring</h2>
            <div className="text-sm text-gray-500">last 24 hours</div>
          </div>
          <AreaChartComponent
            data={data.realTimeData}
            title="System activity trends"
            height={250}
          />
        </div>

        {/* Project data form */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold text-gray-900">Project progress details</h2>
            <button
              onClick={loadData}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
            >
              Refresh data
            </button>
          </div>
          <DataTable
            data={data.projectProgress}
            columns={[
              { key: 'name', label: 'Project name' },
              { key: 'progress', label: 'schedule', format: (value) => `${value}%` },
              { key: 'budget', label: 'Budget', format: (value) => `$${value.toLocaleString()}` },
              { key: 'spent', label: 'spent', format: (value) => `$${value.toLocaleString()}` },
              { key: 'timeline', label: 'timeline', format: (value) => `${value}months` }
            ]}
          />
        </div>

        {/* Cost estimate comparison */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mt-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-6">Comparison of cost estimating methods</h2>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead>
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Estimation method</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Estimate</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">actual value</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">deviation</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Accuracy</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {data.costComparison.map((item: any, index: number) => (
                  <tr key={index}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{item.name}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      ${item.estimate.toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      ${item.actual.toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${item.variance >= 0 ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'}`}>
                        {item.variance >= 0 ? '+' : ''}{item.variance}%
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {Math.round(100 - Math.abs(item.variance))}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-4 text-sm text-gray-500">
            * AIForecasting methods show the highest accuracy in cost estimation
          </div>
        </div>
      </div>
    </div>
  )
}