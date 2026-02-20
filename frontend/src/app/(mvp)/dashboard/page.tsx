'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useAuth } from '@/contexts/AuthContext'
import { LineChartComponent, BarChartComponent, MetricCard } from '@/components/charts'
import { dataApi } from '@/lib/data-generator'

export default function OverviewDashboardPage() {
  const { user } = useAuth()
  const [stats, setStats] = useState({
    totalProjects: 0,
    activeQueries: 0,
    documentsProcessed: 0,
    costSavings: 0
  })
  const [chartData, setChartData] = useState<Array<Record<string, unknown>> | null>(null)

  const loadData = async () => {
    try {
      const kpiData = await dataApi.getKPIMetrics()
      const timeSeriesData = await dataApi.getTimeSeriesData()
      
      setStats({
        totalProjects: kpiData.totalProjects,
        activeQueries: kpiData.activeProjects,
        documentsProcessed: 156, // simulated data
        costSavings: Math.round(kpiData.budgetUtilization * 10000)
      })
      
      setChartData(timeSeriesData.slice(0, 6)) // Only show the last 6 months
    } catch (error) {
      console.error('Failed to load data:', error)
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadData()
  }, [])

  const quickActions = [
    { title: 'Start a new query', description: 'andAIAssistant conversation', href: '/workflow-chat', color: 'blue' },
    { title: 'Upload documents', description: 'Process and analyze documents', href: '/documents', color: 'green' },
    { title: 'Data dashboard', description: 'View detailed analysis', href: '/data-dashboard', color: 'purple' },
    { title: 'cost estimate', description: 'Estimate project costs', href: '/cost-estimation', color: 'orange' }
  ]

  const recentActivities = [
    { id: 1, type: 'query', description: 'Construction cost risks analyzed', time: '10minutes ago' },
    { id: 2, type: 'document', description: 'Project report uploaded.pdf', time: '30minutes ago' },
    { id: 3, type: 'analysis', description: 'Cost analysis chart generated', time: '1hours ago' },
    { id: 4, type: 'system', description: 'System update completed', time: '2hours ago' }
  ]

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* welcome banner */}
        <div className="bg-gradient-to-r from-blue-600 to-blue-800 rounded-2xl p-8 mb-8 text-white">
          <h1 className="text-3xl font-bold mb-2">
            welcome back,{user?.name || 'user'}！
          </h1>
          <p className="text-blue-100">
            you have {stats.activeQueries} active queries and {stats.documentsProcessed} processed documents
          </p>
        </div>

        {/* Statistics cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <MetricCard 
            title="Total number of items" 
            value={stats.totalProjects}
            change="+12%"
          />
          
          <MetricCard 
            title="active query" 
            value={stats.activeQueries}
            change="+3 today"
          />
          
          <MetricCard 
            title="Process documents" 
            value={stats.documentsProcessed}
            change="+8 this week"
          />
          
          <MetricCard 
            title="cost savings" 
            value={`$${stats.costSavings.toLocaleString()}`}
            change="+15% Efficiency improvement"
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Cost Trend Chart */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-6">cost trends</h2>
            {chartData ? (
              <LineChartComponent 
                data={chartData}
                title="Cost changes in the last 6 months"
                height={250}
              />
            ) : (
              <div className="h-64 flex items-center justify-center">
                <div className="text-gray-400">Load chart data...</div>
              </div>
            )}
          </div>

          {/* Project type distribution */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-6">Project type distribution</h2>
            {chartData ? (
              <BarChartComponent 
                data={[
                  { name: 'Residential', value: 35 },
                  { name: 'Business', value: 28 },
                  { name: 'industry', value: 22 },
                  { name: 'infrastructure', value: 15 }
                ]}
                title="Proportion of project types"
                height={250}
              />
            ) : (
              <div className="h-64 flex items-center justify-center">
                <div className="text-gray-400">Load chart data...</div>
              </div>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mt-8">
          {/* Quick operation */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-6">Quick operation</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {quickActions.map((action, index) => (
                <Link
                  key={index}
                  href={action.href}
                  className={`p-4 rounded-lg border border-gray-200 hover:border-${action.color}-300 hover:bg-${action.color}-50 transition group`}
                >
                  <div className={`text-${action.color}-600 font-medium mb-1`}>{action.title}</div>
                  <div className="text-sm text-gray-600">{action.description}</div>
                  <div className="mt-2 text-sm text-gray-400 group-hover:text-gray-600">
                    Click to start →
                  </div>
                </Link>
              ))}
            </div>
          </div>

          {/* Recent activities */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-6">Recent activities</h2>
            <div className="space-y-4">
              {recentActivities.map((activity) => (
                <div key={activity.id} className="flex items-start space-x-3">
                  <div className={`w-2 h-2 mt-2 rounded-full ${
                    activity.type === 'query' ? 'bg-blue-500' :
                    activity.type === 'document' ? 'bg-green-500' :
                    activity.type === 'analysis' ? 'bg-purple-500' : 'bg-gray-500'
                  }`}></div>
                  <div className="flex-1">
                    <div className="text-sm text-gray-900">{activity.description}</div>
                    <div className="text-xs text-gray-500">{activity.time}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* System status */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mt-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-6">System status</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="p-4 bg-gray-50 rounded-lg">
              <div className="text-sm font-medium text-gray-500">Front-end service</div>
              <div className="flex items-center mt-2">
                <div className="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
                <div className="text-green-600 font-medium">Running normally</div>
              </div>
            </div>
            
            <div className="p-4 bg-gray-50 rounded-lg">
              <div className="text-sm font-medium text-gray-500">rear endAPI</div>
              <div className="flex items-center mt-2">
                <div className="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
                <div className="text-green-600 font-medium">Running normally</div>
              </div>
            </div>
            
            <div className="p-4 bg-gray-50 rounded-lg">
              <div className="text-sm font-medium text-gray-500">data visualization</div>
              <div className="flex items-center mt-2">
                <div className="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
                <div className="text-green-600 font-medium">Enabled</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
