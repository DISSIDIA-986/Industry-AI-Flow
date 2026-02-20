// Simulation Data Generator
export class MockDataGenerator {
  // Generate time series data
  static generateTimeSeriesData(count: number = 12, startValue: number = 100) {
    const months = ['1moon', '2moon', '3moon', '4moon', '5moon', '6moon', '7moon', '8moon', '9moon', '10moon', '11moon', '12moon']
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
  
  // Generate categorical data
  static generateCategoryData(categories: string[] = ['Residential', 'Business', 'industry', 'infrastructure', 'medical']) {
    return categories.map(category => ({
      name: category,
      value: Math.round(50 + Math.random() * 200),
      cost: Math.round(100000 + Math.random() * 500000),
      risk: Math.round(Math.random() * 100)
    }))
  }
  
  // Generate cost distribution data
  static generateCostDistribution() {
    const categories = ['Material', 'Artificial', 'equipment', 'manage', 'other']
    return categories.map(category => ({
      name: category,
      value: Math.round(20 + Math.random() * 50)
    }))
  }
  
  // Generate risk radar chart data
  static generateRiskRadarData() {
    const subjects = ['cost risk', 'time risk', 'quality risk', 'security risk', 'Compliance risk', 'technology risk']
    return subjects.map(subject => ({
      subject,
      value: Math.round(60 + Math.random() * 40)
    }))
  }
  
  // Generate project progress data
  static generateProjectProgress() {
    const projects = ['office buildingA', 'HospitalB', 'SchoolC', 'shopping mallD', 'ResidentialE']
    return projects.map(project => ({
      name: project,
      progress: Math.round(Math.random() * 100),
      budget: Math.round(500000 + Math.random() * 2000000),
      spent: Math.round(400000 + Math.random() * 1500000),
      timeline: Math.round(6 + Math.random() * 12)
    }))
  }
  
  // generateKPIIndicator data
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
  
  // Generate real-time monitoring data
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
  
  // Generate cost estimate comparison data
  static generateCostComparison() {
    const methods = ['historical data', 'Expert assessment', 'AIpredict', 'market benchmark']
    return methods.map(method => ({
      name: method,
      estimate: Math.round(1000000 + Math.random() * 500000),
      actual: Math.round(900000 + Math.random() * 600000),
      variance: Math.round((Math.random() * 20 - 10) * 100) / 100
    }))
  }
}

// dataAPI
export const dataApi = {
  // Get time series data
  async getTimeSeriesData() {
    await new Promise(resolve => setTimeout(resolve, 300))
    return MockDataGenerator.generateTimeSeriesData()
  },
  
  // Get categorical data
  async getCategoryData() {
    await new Promise(resolve => setTimeout(resolve, 300))
    return MockDataGenerator.generateCategoryData()
  },
  
  // Get cost distribution data
  async getCostDistribution() {
    await new Promise(resolve => setTimeout(resolve, 300))
    return MockDataGenerator.generateCostDistribution()
  },
  
  // Get risk data
  async getRiskData() {
    await new Promise(resolve => setTimeout(resolve, 300))
    return MockDataGenerator.generateRiskRadarData()
  },
  
  // Get project progress data
  async getProjectProgress() {
    await new Promise(resolve => setTimeout(resolve, 300))
    return MockDataGenerator.generateProjectProgress()
  },
  
  // GetKPIindex
  async getKPIMetrics() {
    await new Promise(resolve => setTimeout(resolve, 300))
    return MockDataGenerator.generateKPIMetrics()
  },
  
  // Get real-time data
  async getRealTimeData() {
    await new Promise(resolve => setTimeout(resolve, 300))
    return MockDataGenerator.generateRealTimeData()
  },
  
  // Get cost comparison data
  async getCostComparison() {
    await new Promise(resolve => setTimeout(resolve, 300))
    return MockDataGenerator.generateCostComparison()
  },
  
  // Get all data
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

// Export
export default dataApi