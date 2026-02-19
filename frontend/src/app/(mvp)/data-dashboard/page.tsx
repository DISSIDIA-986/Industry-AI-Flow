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
      console.error('加载数据失败:', error)
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
        {/* 标题和时间筛选 */}
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-3xl font-bold text-gray-900">数据分析仪表板</h1>
          <div className="flex space-x-2">
            <button
              onClick={() => setTimeRange('daily')}
              className={`px-4 py-2 rounded-lg ${timeRange === 'daily' ? 'bg-blue-600 text-white' : 'bg-white text-gray-700 border border-gray-300'}`}
            >
              日度
            </button>
            <button
              onClick={() => setTimeRange('weekly')}
              className={`px-4 py-2 rounded-lg ${timeRange === 'weekly' ? 'bg-blue-600 text-white' : 'bg-white text-gray-700 border border-gray-300'}`}
            >
              周度
            </button>
            <button
              onClick={() => setTimeRange('monthly')}
              className={`px-4 py-2 rounded-lg ${timeRange === 'monthly' ? 'bg-blue-600 text-white' : 'bg-white text-gray-700 border border-gray-300'}`}
            >
              月度
            </button>
          </div>
        </div>

        {/* KPI 指标卡片 */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <MetricCard
            title="总项目数"
            value={data.kpiMetrics.totalProjects}
            change="+12%"
          />
          <MetricCard
            title="活跃项目"
            value={data.kpiMetrics.activeProjects}
            change="+5%"
          />
          <MetricCard
            title="预算利用率"
            value={`${data.kpiMetrics.budgetUtilization}%`}
            change="+3.2%"
          />
          <MetricCard
            title="风险评分"
            value={`${data.kpiMetrics.riskScore}/100`}
            change="-8%"
          />
        </div>

        {/* 第一行图表 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* 成本趋势图 */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-6">成本趋势分析</h2>
            <LineChartComponent
              data={data.timeSeries}
              title="月度成本变化"
              height={300}
            />
          </div>

          {/* 项目类型分布 */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-6">项目类型分布</h2>
            <PieChartComponent
              data={data.category}
              title="项目类型占比"
              height={300}
            />
          </div>
        </div>

        {/* 第二行图表 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* 成本构成分析 */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-6">成本构成分析</h2>
            <BarChartComponent
              data={data.costDistribution}
              title="成本构成比例"
              height={300}
            />
          </div>

          {/* 风险评估雷达图 */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-6">风险评估</h2>
            <RadarChartComponent
              data={data.riskData}
              title="风险维度评估"
              height={300}
            />
          </div>
        </div>

        {/* 实时监控 */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold text-gray-900">实时系统监控</h2>
            <div className="text-sm text-gray-500">最近24小时</div>
          </div>
          <AreaChartComponent
            data={data.realTimeData}
            title="系统活动趋势"
            height={250}
          />
        </div>

        {/* 项目数据表格 */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold text-gray-900">项目进度详情</h2>
            <button
              onClick={loadData}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
            >
              刷新数据
            </button>
          </div>
          <DataTable
            data={data.projectProgress}
            columns={[
              { key: 'name', label: '项目名称' },
              { key: 'progress', label: '进度', format: (value) => `${value}%` },
              { key: 'budget', label: '预算', format: (value) => `$${value.toLocaleString()}` },
              { key: 'spent', label: '已花费', format: (value) => `$${value.toLocaleString()}` },
              { key: 'timeline', label: '时间线', format: (value) => `${value}个月` }
            ]}
          />
        </div>

        {/* 成本估算对比 */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mt-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-6">成本估算方法对比</h2>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead>
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">估算方法</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">估算值</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">实际值</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">偏差</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">准确率</th>
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
            * AI预测方法在成本估算中表现出最高的准确率
          </div>
        </div>
      </div>
    </div>
  )
}