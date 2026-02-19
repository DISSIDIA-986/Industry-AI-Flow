'use client'

import { useState } from 'react'
import { 
  Form, FormGroup, Input, Select, Button, 
  Card, CardHeader, CardTitle, CardContent,
  Table, TableHead, TableHeader, TableBody, TableRow, TableCell,
  Loading, ErrorDisplay
} from '@/components'
import { predictCost, predictCostBatch, type CostProjectFeatures } from '@/lib/api-client'

const projectTypes = [
  { value: 'commercial_office', label: '商业办公楼' },
  { value: 'residential_highrise', label: '高层住宅' },
  { value: 'hospital', label: '医院' },
  { value: 'school', label: '学校' },
  { value: 'shopping_mall', label: '购物中心' },
  { value: 'industrial', label: '工业建筑' }
]

const locations = [
  { value: 'Toronto', label: '多伦多' },
  { value: 'Vancouver', label: '温哥华' },
  { value: 'Montreal', label: '蒙特利尔' },
  { value: 'Calgary', label: '卡尔加里' },
  { value: 'Edmonton', label: '埃德蒙顿' }
]

const initialProject: CostProjectFeatures = {
  project_type: 'commercial_office',
  location: 'Toronto',
  sqft: 185000,
  floors: 18,
  num_units: 1,
  planned_duration_weeks: 78,
  estimated_cost_cad: 72000000,
  contractor_rating: 4.2,
  complexity_score: 7,
  team_experience_years: 11,
  num_change_orders: 5,
  weather_risk_factor: 0.32,
  material_volatility: 0.44,
  num_subcontractors: 16,
  budget_pressure: 0.58,
  risk_score: 6.8,
  risk_score_original: 6.3,
}

export default function CostEstimationPage() {
  const [project, setProject] = useState<CostProjectFeatures>(initialProject)
  const [confidence, setConfidence] = useState(0.9)
  const [singleResult, setSingleResult] = useState<any>(null)
  const [batchRows, setBatchRows] = useState<CostProjectFeatures[]>([])
  const [batchResults, setBatchResults] = useState<any[]>([])
  const [loadingSingle, setLoadingSingle] = useState(false)
  const [loadingBatch, setLoadingBatch] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const updateField = (field: keyof CostProjectFeatures, value: string | number) => {
    setProject(prev => ({ ...prev, [field]: value }))
  }

  const handleSinglePrediction = async () => {
    setLoadingSingle(true)
    setError(null)
    try {
      const response = await predictCost({} as any, project, confidence)
      setSingleResult(response.prediction)
    } catch (err) {
      setError(err instanceof Error ? err.message : '预测失败')
    } finally {
      setLoadingSingle(false)
    }
  }

  const handleBatchPrediction = async () => {
    if (batchRows.length === 0) return
    
    setLoadingBatch(true)
    setError(null)
    try {
      const response = await predictCostBatch({} as any, batchRows, confidence)
      setBatchResults(response.predictions)
    } catch (err) {
      setError(err instanceof Error ? err.message : '批量预测失败')
    } finally {
      setLoadingBatch(false)
    }
  }

  const addToBatch = () => {
    setBatchRows(prev => [...prev, { ...project }])
  }

  const clearBatch = () => {
    setBatchRows([])
    setBatchResults([])
  }

  return (
    <div className="max-w-7xl mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">成本估算</h1>
        <p className="text-gray-600 mt-2">
          使用结构化回归模型进行建筑成本预测，而非自由形式的LLM猜测
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* 单项目预测 */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>单项目成本预测</CardTitle>
          </CardHeader>
          <CardContent>
            <Form>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <FormGroup label="项目类型">
                  <Select
                    value={project.project_type}
                    onChange={(e) => updateField('project_type', e.target.value)}
                    options={projectTypes}
                  />
                </FormGroup>

                <FormGroup label="地点">
                  <Select
                    value={project.location}
                    onChange={(e) => updateField('location', e.target.value)}
                    options={locations}
                  />
                </FormGroup>

                <FormGroup label="建筑面积 (平方英尺)">
                  <Input
                    type="number"
                    value={project.sqft}
                    onChange={(e) => updateField('sqft', parseFloat(e.target.value))}
                  />
                </FormGroup>

                <FormGroup label="楼层数">
                  <Input
                    type="number"
                    value={project.floors}
                    onChange={(e) => updateField('floors', parseInt(e.target.value))}
                  />
                </FormGroup>

                <FormGroup label="预计成本 (CAD)">
                  <Input
                    type="number"
                    value={project.estimated_cost_cad}
                    onChange={(e) => updateField('estimated_cost_cad', parseFloat(e.target.value))}
                  />
                </FormGroup>

                <FormGroup label="承包商评分 (1-5)">
                  <Input
                    type="number"
                    step="0.1"
                    min="1"
                    max="5"
                    value={project.contractor_rating}
                    onChange={(e) => updateField('contractor_rating', parseFloat(e.target.value))}
                  />
                </FormGroup>

                <FormGroup label="复杂度评分 (1-10)">
                  <Input
                    type="number"
                    min="1"
                    max="10"
                    value={project.complexity_score}
                    onChange={(e) => updateField('complexity_score', parseInt(e.target.value))}
                  />
                </FormGroup>

                <FormGroup label="团队经验 (年)">
                  <Input
                    type="number"
                    value={project.team_experience_years}
                    onChange={(e) => updateField('team_experience_years', parseInt(e.target.value))}
                  />
                </FormGroup>
              </div>

              <div className="mt-6">
                <FormGroup label={`置信度: ${Math.round(confidence * 100)}%`}>
                  <Input
                    type="range"
                    min="0.5"
                    max="0.99"
                    step="0.01"
                    value={confidence}
                    onChange={(e) => setConfidence(parseFloat(e.target.value))}
                    className="w-full"
                  />
                </FormGroup>
              </div>

              <div className="flex space-x-4 mt-6">
                <Button
                  onClick={handleSinglePrediction}
                  loading={loadingSingle}
                  disabled={loadingSingle}
                >
                  预测成本
                </Button>
                <Button
                  variant="secondary"
                  onClick={addToBatch}
                >
                  添加到批量队列
                </Button>
              </div>

              {error && (
                <div className="mt-4">
                  <ErrorDisplay message={error} />
                </div>
              )}

              {singleResult && !loadingSingle && (
                <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="bg-blue-50 p-4 rounded-lg">
                    <div className="text-sm text-blue-600 font-medium">预测实际成本</div>
                    <div className="text-2xl font-bold text-gray-900 mt-1">
                      ${singleResult.predicted_actual_cost_cad?.toLocaleString() || 'N/A'}
                    </div>
                  </div>
                  <div className="bg-green-50 p-4 rounded-lg">
                    <div className="text-sm text-green-600 font-medium">预测超支率</div>
                    <div className="text-2xl font-bold text-gray-900 mt-1">
                      {singleResult.predicted_cost_overrun_pct?.toFixed(1) || 'N/A'}%
                    </div>
                  </div>
                  <div className="bg-purple-50 p-4 rounded-lg">
                    <div className="text-sm text-purple-600 font-medium">预测区间</div>
                    <div className="text-sm text-gray-900 mt-1">
                      ${singleResult.prediction_interval_cad?.lower?.toLocaleString() || 'N/A'} - 
                      ${singleResult.prediction_interval_cad?.upper?.toLocaleString() || 'N/A'}
                    </div>
                  </div>
                </div>
              )}
            </Form>
          </CardContent>
        </Card>

        {/* 批量预测 */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>批量预测队列 ({batchRows.length})</CardTitle>
              <div className="flex space-x-2">
                <Button
                  onClick={handleBatchPrediction}
                  loading={loadingBatch}
                  disabled={batchRows.length === 0 || loadingBatch}
                >
                  运行批量预测
                </Button>
                <Button
                  variant="outline"
                  onClick={clearBatch}
                >
                  清空队列
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {batchRows.length > 0 ? (
              <div className="space-y-4">
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableHeader>项目类型</TableHeader>
                      <TableHeader>地点</TableHeader>
                      <TableHeader>建筑面积</TableHeader>
                      <TableHeader>预计成本</TableHeader>
                      <TableHeader>风险评分</TableHeader>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {batchRows.map((row, index) => (
                      <TableRow key={index}>
                        <TableCell>
                          {projectTypes.find(p => p.value === row.project_type)?.label || row.project_type}
                        </TableCell>
                        <TableCell>{row.location}</TableCell>
                        <TableCell>{row.sqft.toLocaleString()} sqft</TableCell>
                        <TableCell>${row.estimated_cost_cad.toLocaleString()}</TableCell>
                        <TableCell>{row.risk_score}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>

                {batchResults.length > 0 && (
                  <div className="mt-6">
                    <h4 className="text-lg font-semibold text-gray-900 mb-4">批量预测结果</h4>
                    <Table>
                      <TableHead>
                        <TableRow>
                          <TableHeader>#</TableHeader>
                          <TableHeader>预测成本</TableHeader>
                          <TableHeader>超支率</TableHeader>
                          <TableHeader>预测区间</TableHeader>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {batchResults.map((result, index) => (
                          <TableRow key={index}>
                            <TableCell>{index + 1}</TableCell>
                            <TableCell>
                              ${result.predicted_actual_cost_cad?.toLocaleString() || 'N/A'}
                            </TableCell>
                            <TableCell>
                              {result.predicted_cost_overrun_pct?.toFixed(1) || 'N/A'}%
                            </TableCell>
                            <TableCell>
                              ${result.prediction_interval_cad?.lower?.toLocaleString() || 'N/A'} - 
                              ${result.prediction_interval_cad?.upper?.toLocaleString() || 'N/A'}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">
                从上方表单添加项目到批量队列
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}