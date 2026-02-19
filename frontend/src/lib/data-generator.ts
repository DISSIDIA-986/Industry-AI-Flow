// 模拟数据生成器
export class MockDataGenerator {
  // 生成时间序列数据
  static generateTimeSeriesData(count: number = 12, startValue: number = 100) {
    const months = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']
    const data = []
    
    for (let i = 0; i < count; i++) {
      const value = startValue + Math.random() * 50 - 25
      data.push({
        name: months[i % months.length],
        value: Math.round(value),
        actual: Math.round(value * (0.9 + Math.random() * 0.2)),
        target: Math.round(startValue * (1 + i * 0.05))
      })
    }
    
    return data
  }
  
  // 生成分类数据
  static generateCategoryData(categories: string[] = ['住宅', '商业', '工业', '基础设施', '医疗']) {
    return categories.map(category => ({
      name: category,
      value: Math.round(50 + Math.random() * 200),
      cost: Math.round(100000 + Math.random() * 500000),
      risk: Math.round(Math.random() * 100)
    }))
  }
  
  // 生成成本分布数据
  static generateCostDistribution() {
    const categories = ['材料', '人工', '设备', '管理', '其他']
    return categories.map(category => ({
      name: category,
      value: Math.round(20 + Math.random() * 50)
    }))
  }
  
  // 生成风险雷达图数据
  static generateRiskRadarData() {
    const subjects = ['成本风险', '时间风险', '质量风险', '安全风险', '合规风险', '技术风险']
    return subjects.map(subject => ({
      subject,
      value: Math.round(60 + Math.random() * 40)
    }))
  }
  
  // 生成项目进度数据
  static generateProjectProgress() {
    const projects = ['办公楼A', '医院B', '学校C', '商场D', '住宅E']
    return projects.map(project => ({
      name: project,
      progress: Math.round(Math.random() * 100),
      budget: Math.round(500000 + Math.random() * 2000000),
      spent: Math.round(400000 + Math.random() * 1500000),
      timeline: Math.round(6 + Math.random() * 12)
    }))
  }
  
  // 生成KPI指标数据
  static generateKPIMetrics() {
    return {
      totalProjects: Math.round(50 + Math.random() * 100),
      activeProjects: Math.round(15 + Math.random() * 20),
      budgetUtilization: Math.round(75 + Math.random() * 20),
      riskScore: Math.round(30 + Math.random() * 40),
      avgCostVariance: Math.round(-5 + Math.random() * 15),
      completionRate: Math.round(85 + Math.random() * 10)
    }
  }
  
  // 生成实时监控数据
  static generateRealTimeData() {
    const now = new Date()
    const data = []
    
    for (let i = 0; i < 24; i++) {
      const hour = (now.getHours() - i + 24) % 24
      data.push({
        time: `${hour}:00`,
        queries: Math.round(10 + Math.random() * 50),
        documents: Math.round(5 + Math.random() * 20),
        users: Math.round(3 + Math.random() * 10),
        errors: Math.round(Math.random() * 5)
      })
    }
    
    return data.reverse()
  }
  
  // 生成成本估算对比数据
  static generateCostComparison() {
    const methods = ['历史数据', '专家评估', 'AI预测', '市场基准']
    return methods.map(method => ({
      name: method,
      estimate: Math.round(1000000 + Math.random() * 500000),
      actual: Math.round(900000 + Math.random() * 600000),
      variance: Math.round((Math.random() * 20 - 10) * 100) / 100
    }))
  }
}

// 数据API
export const dataApi = {
  // 获取时间序列数据
  async getTimeSeriesData() {
    await new Promise(resolve => setTimeout(resolve, 300))
    return MockDataGenerator.generateTimeSeriesData()
  },
  
  // 获取分类数据
  async getCategoryData() {
    await new Promise(resolve => setTimeout(resolve, 300))
    return MockDataGenerator.generateCategoryData()
  },
  
  // 获取成本分布数据
  async getCostDistribution() {
    await new Promise(resolve => setTimeout(resolve, 300))
    return MockDataGenerator.generateCostDistribution()
  },
  
  // 获取风险数据
  async getRiskData() {
    await new Promise(resolve => setTimeout(resolve, 300))
    return MockDataGenerator.generateRiskRadarData()
  },
  
  // 获取项目进度数据
  async getProjectProgress() {
    await new Promise(resolve => setTimeout(resolve, 300))
    return MockDataGenerator.generateProjectProgress()
  },
  
  // 获取KPI指标
  async getKPIMetrics() {
    await new Promise(resolve => setTimeout(resolve, 300))
    return MockDataGenerator.generateKPIMetrics()
  },
  
  // 获取实时数据
  async getRealTimeData() {
    await new Promise(resolve => setTimeout(resolve, 300))
    return MockDataGenerator.generateRealTimeData()
  },
  
  // 获取成本对比数据
  async getCostComparison() {
    await new Promise(resolve => setTimeout(resolve, 300))
    return MockDataGenerator.generateCostComparison()
  },
  
  // 获取所有数据
  async getAllData() {
    await new Promise(resolve => setTimeout(resolve, 500))
    return {
      timeSeries: MockDataGenerator.generateTimeSeriesData(),
      category: MockDataGenerator.generateCategoryData(),
      costDistribution: MockDataGenerator.generateCostDistribution(),
      riskData: MockDataGenerator.generateRiskRadarData(),
      projectProgress: MockDataGenerator.generateProjectProgress(),
      kpiMetrics: MockDataGenerator.generateKPIMetrics(),
      realTimeData: MockDataGenerator.generateRealTimeData(),
      costComparison: MockDataGenerator.generateCostComparison()
    }
  }
}

// 导出
export default dataApi