'use client'

import { 
  LineChart as RechartsLineChart, Line, BarChart as RechartsBarChart, Bar, PieChart, Pie, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  Cell, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis
} from 'recharts'

interface ChartProps {
  data: any[]
  width?: number | `${number}%`
  height?: number | `${number}%`
  title?: string
}

// Basic chart components
export function LineChartComponent({ data, width = '100%', height = 300, title }: ChartProps) {
  return (
    <div className="w-full">
      {title && <h3 className="text-lg font-medium text-gray-900 mb-4">{title}</h3>}
      <ResponsiveContainer width={width} height={height}>
        <RechartsLineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="name" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Line type="monotone" dataKey="value" stroke="#3b82f6" strokeWidth={2} />
        </RechartsLineChart>
      </ResponsiveContainer>
    </div>
  )
}

// Compatibility aliases for legacy imports.
export const LineChart = LineChartComponent

// Bar chart component
export function BarChartComponent({ data, width = '100%', height = 300, title }: ChartProps) {
  return (
    <div className="w-full">
      {title && <h3 className="text-lg font-medium text-gray-900 mb-4">{title}</h3>}
      <ResponsiveContainer width={width} height={height}>
        <RechartsBarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="name" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Bar dataKey="value" fill="#10b981" radius={[4, 4, 0, 0]} />
        </RechartsBarChart>
      </ResponsiveContainer>
    </div>
  )
}

// Compatibility aliases for legacy imports.
export const BarChart = BarChartComponent

// Pie chart component
export function PieChartComponent({ data, width = '100%', height = 300, title }: ChartProps) {
  const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']
  
  return (
    <div className="w-full">
      {title && <h3 className="text-lg font-medium text-gray-900 mb-4">{title}</h3>}
      <ResponsiveContainer width={width} height={height}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={({ name, percent }) => {
              const safePercent = typeof percent === 'number' ? percent : 0
              return `${String(name)}: ${(safePercent * 100).toFixed(0)}%`
            }}
            outerRadius={80}
            fill="#8884d8"
            dataKey="value"
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}

// Area chart component
export function AreaChartComponent({ data, width = '100%', height = 300, title }: ChartProps) {
  return (
    <div className="w-full">
      {title && <h3 className="text-lg font-medium text-gray-900 mb-4">{title}</h3>}
      <ResponsiveContainer width={width} height={height}>
        <AreaChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="name" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Area type="monotone" dataKey="value" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.3} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

// Radar chart component
export function RadarChartComponent({ data, width = '100%', height = 300, title }: ChartProps) {
  return (
    <div className="w-full">
      {title && <h3 className="text-lg font-medium text-gray-900 mb-4">{title}</h3>}
      <ResponsiveContainer width={width} height={height}>
        <RadarChart cx="50%" cy="50%" outerRadius="80%" data={data}>
          <PolarGrid />
          <PolarAngleAxis dataKey="subject" />
          <PolarRadiusAxis />
          <Radar name="index" dataKey="value" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.6} />
          <Tooltip />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  )
}

// Dashboard card component
export function MetricCard({ title, value, change, icon }: { 
  title: string
  value: string | number
  change?: string
  icon?: React.ReactNode
}) {
  const isPositive = change?.startsWith('+')
  
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="text-sm font-medium text-gray-500">{title}</div>
        {icon && <div className="text-gray-400">{icon}</div>}
      </div>
      <div className="text-2xl font-bold text-gray-900">{value}</div>
      {change && (
        <div className={`mt-2 text-sm font-medium ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
          {change}
        </div>
      )}
    </div>
  )
}

// Data table component
export function DataTable({ data, columns }: { 
  data: any[]
  columns: { key: string; label: string; format?: (value: any) => string }[]
}) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead>
          <tr>
            {columns.map((column) => (
              <th
                key={column.key}
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
              >
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {data.map((row, index) => (
            <tr key={index}>
              {columns.map((column) => (
                <td key={column.key} className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {column.format ? column.format(row[column.key]) : row[column.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// Export all components
export default {
  LineChart: LineChartComponent,
  BarChart: BarChartComponent,
  PieChart: PieChartComponent,
  AreaChart: AreaChartComponent,
  RadarChart: RadarChartComponent,
  MetricCard,
  DataTable
}
