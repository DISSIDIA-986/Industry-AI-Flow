'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useAuth } from '@/contexts/AuthContext'
import { LineChart, BarChart, MetricCard } from '@/components/charts'
import { dataApi } from '@/lib/data-generator'

export default function SimpleDashboardPage() {
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
    { title: 'Start a New Query', description: 'Chat with the AI assistant', href: '/workflow-chat', color: 'blue' },
    { title: 'Upload Documents', description: 'Process and analyze documents', href: '/documents', color: 'green' },
    { title: 'Data Dashboard', description: 'View detailed analysis', href: '/data-dashboard', color: 'purple' },
    { title: 'Cost Estimation', description: 'Estimate project costs', href: '/cost-estimation', color: 'orange' }
  ]

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* welcome banner */}
        <div className="bg-gradient-to-r from-blue-600 to-blue-800 rounded-2xl p-8 mb-8 text-white">
          <h1 className="text-3xl font-bold mb-2">
            Welcome back, {user?.name || 'User'}!
          </h1>
          <p className="text-blue-100">
            You have {stats.activeQueries} active queries and {stats.documentsProcessed} processed documents
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
              <LineChart 
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
              <BarChart 
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

        {/* Quick operation */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mt-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-6">Quick operation</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
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
      </div>
    </div>
  )
}
