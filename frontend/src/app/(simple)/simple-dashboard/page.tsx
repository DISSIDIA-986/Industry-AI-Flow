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
        documentsProcessed: 156, // 模拟数据
        costSavings: Math.round(kpiData.budgetUtilization * 10000)
      })
      
      setChartData(timeSeriesData.slice(0, 6)) // 只显示最近6个月
    } catch (error) {
      console.error('加载数据失败:', error)
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadData()
  }, [])

  const quickActions = [
    { title: '开始新查询', description: '与AI助手对话', href: '/workflow-chat', color: 'blue' },
    { title: '上传文档', description: '处理和分析文档', href: '/documents', color: 'green' },
    { title: '数据仪表板', description: '查看详细分析', href: '/data-dashboard', color: 'purple' },
    { title: '成本估算', description: '估算项目成本', href: '/cost-estimation', color: 'orange' }
  ]

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* 欢迎横幅 */}
        <div className="bg-gradient-to-r from-blue-600 to-blue-800 rounded-2xl p-8 mb-8 text-white">
          <h1 className="text-3xl font-bold mb-2">
            欢迎回来，{user?.name || '用户'}！
          </h1>
          <p className="text-blue-100">
            您有 {stats.activeQueries} 个活跃查询和 {stats.documentsProcessed} 个已处理文档
          </p>
        </div>

        {/* 统计卡片 */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <MetricCard 
            title="总项目数" 
            value={stats.totalProjects}
            change="+12%"
          />
          
          <MetricCard 
            title="活跃查询" 
            value={stats.activeQueries}
            change="+3 今日"
          />
          
          <MetricCard 
            title="处理文档" 
            value={stats.documentsProcessed}
            change="+8 本周"
          />
          
          <MetricCard 
            title="成本节省" 
            value={`$${stats.costSavings.toLocaleString()}`}
            change="+15% 效率提升"
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* 成本趋势图表 */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-6">成本趋势</h2>
            {chartData ? (
              <LineChart 
                data={chartData}
                title="最近6个月成本变化"
                height={250}
              />
            ) : (
              <div className="h-64 flex items-center justify-center">
                <div className="text-gray-400">加载图表数据...</div>
              </div>
            )}
          </div>

          {/* 项目类型分布 */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-6">项目类型分布</h2>
            {chartData ? (
              <BarChart 
                data={[
                  { name: '住宅', value: 35 },
                  { name: '商业', value: 28 },
                  { name: '工业', value: 22 },
                  { name: '基础设施', value: 15 }
                ]}
                title="项目类型占比"
                height={250}
              />
            ) : (
              <div className="h-64 flex items-center justify-center">
                <div className="text-gray-400">加载图表数据...</div>
              </div>
            )}
          </div>
        </div>

        {/* 快速操作 */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mt-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-6">快速操作</h2>
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
                  点击开始 →
                </div>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
