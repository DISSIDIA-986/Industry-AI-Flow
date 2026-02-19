/**
 * 测试数据工厂
 * 生成各种测试场景所需的数据
 */

/**
 * 生成测试用户数据
 */
export function createTestUserData() {
  const timestamp = Date.now();
  return {
    email: `test.user.${timestamp}@example.com`,
    password: 'TestPassword123!@#',
    firstName: 'Test',
    lastName: `User${timestamp}`,
    company: 'Test Company Inc.',
    role: 'Software Engineer',
    phone: `+1${Math.floor(Math.random() * 10000000000)}`
  };
}

/**
 * 生成测试文档数据
 */
export function createTestDocumentData() {
  const documentTypes = ['PDF', 'DOCX', 'XLSX', 'PPTX', 'TXT', 'CSV', 'JSON'];
  const industries = ['Technology', 'Finance', 'Healthcare', 'Education', 'Manufacturing'];
  const departments = ['Engineering', 'Marketing', 'Sales', 'HR', 'Finance'];
  
  const type = documentTypes[Math.floor(Math.random() * documentTypes.length)];
  const industry = industries[Math.floor(Math.random() * industries.length)];
  const department = departments[Math.floor(Math.random() * departments.length)];
  const timestamp = new Date().toISOString().split('T')[0];
  
  return {
    name: `${industry}_${department}_Report_${timestamp}.${type.toLowerCase()}`,
    type,
    size: Math.floor(Math.random() * 10000000) + 1000, // 1KB - 10MB
    uploadedAt: new Date().toISOString(),
    uploadedBy: `user${Math.floor(Math.random() * 1000)}@company.com`,
    tags: [industry.toLowerCase(), department.toLowerCase(), 'report', 'analysis'],
    description: `This is a test ${type} document for ${industry} ${department} department.`,
    confidential: Math.random() > 0.7
  };
}

/**
 * 生成测试聊天消息
 */
export function createTestChatMessage() {
  const messageTypes = [
    'question',
    'instruction', 
    'analysis_request',
    'code_review',
    'document_summary',
    'data_analysis'
  ];
  
  const messageTemplates = {
    question: [
      'Can you explain how {feature} works?',
      'What are the benefits of using {system}?',
      'How do I {action} in the application?'
    ],
    instruction: [
      'Please analyze {document} and provide key insights',
      'Generate a summary of {topic}',
      'Create a cost estimate for {project}'
    ],
    analysis_request: [
      'Analyze the data in {file} and identify trends',
      'Compare {metric} across different {dimension}',
      'Provide statistical analysis for {dataset}'
    ]
  };
  
  const type = messageTypes[Math.floor(Math.random() * messageTypes.length)];
  const template = messageTemplates[type as keyof typeof messageTemplates]?.[0] || 'Test message';
  
  return {
    type,
    content: template.replace('{feature}', 'the AI workflow system')
                     .replace('{system}', 'Industry AI Flow')
                     .replace('{action}', 'upload documents')
                     .replace('{document}', 'the quarterly report')
                     .replace('{topic}', 'machine learning applications')
                     .replace('{project}', 'a new web application')
                     .replace('{file}', 'sales_data.csv')
                     .replace('{metric}', 'user engagement')
                     .replace('{dimension}', 'time periods')
                     .replace('{dataset}', 'customer feedback'),
    timestamp: new Date().toISOString(),
    sender: 'user',
    metadata: {
      language: 'en',
      length: template.length,
      containsCode: type === 'code_review',
      requiresAnalysis: type === 'analysis_request'
    }
  };
}

/**
 * 生成测试成本估算数据
 */
export function createTestCostEstimationData() {
  const projectTypes = ['Web Application', 'Mobile App', 'Data Pipeline', 'ML Model', 'API Service'];
  const complexities = ['simple', 'medium', 'complex', 'very-complex'];
  const timelines = [30, 60, 90, 120, 180]; // days
  
  const projectType = projectTypes[Math.floor(Math.random() * projectTypes.length)];
  const complexity = complexities[Math.floor(Math.random() * complexities.length)];
  const timeline = timelines[Math.floor(Math.random() * timelines.length)];
  
  // 基础成本计算
  const baseCosts = {
    'Web Application': { simple: 10000, medium: 25000, complex: 50000, 'very-complex': 100000 },
    'Mobile App': { simple: 15000, medium: 35000, complex: 70000, 'very-complex': 140000 },
    'Data Pipeline': { simple: 20000, medium: 45000, complex: 90000, 'very-complex': 180000 },
    'ML Model': { simple: 30000, medium: 60000, complex: 120000, 'very-complex': 240000 },
    'API Service': { simple: 8000, medium: 20000, complex: 40000, 'very-complex': 80000 }
  };
  
  const baseCost = baseCosts[projectType as keyof typeof baseCosts]?.[complexity as keyof typeof baseCosts[keyof typeof baseCosts]] || 25000;
  
  // 时间调整因子
  const timeFactor = timeline < 60 ? 1.2 : timeline > 120 ? 0.9 : 1.0;
  
  // 团队规模影响
  const teamSize = Math.floor(Math.random() * 10) + 3;
  const teamFactor = 1 + (teamSize - 3) * 0.1;
  
  // 最终估算
  const estimatedCost = Math.round(baseCost * timeFactor * teamFactor);
  
  return {
    projectType,
    complexity,
    timeline,
    teamSize,
    estimatedCost,
    breakdown: {
      development: Math.round(estimatedCost * 0.6),
      testing: Math.round(estimatedCost * 0.2),
      deployment: Math.round(estimatedCost * 0.1),
      maintenance: Math.round(estimatedCost * 0.1)
    },
    assumptions: [
      `Project type: ${projectType}`,
      `Complexity level: ${complexity}`,
      `Timeline: ${timeline} days`,
      `Team size: ${teamSize} people`,
      'Based on industry standard rates'
    ]
  };
}

/**
 * 生成测试仪表板数据
 */
export function createTestDashboardData() {
  const metrics = {
    activeUsers: Math.floor(Math.random() * 1000) + 100,
    documentsProcessed: Math.floor(Math.random() * 5000) + 1000,
    chatMessages: Math.floor(Math.random() * 10000) + 5000,
    costSavings: Math.floor(Math.random() * 100000) + 50000,
    accuracyRate: Math.random() * 20 + 80, // 80-100%
    responseTime: Math.random() * 500 + 100 // 100-600ms
  };
  
  // 生成时间序列数据
  const timeSeries = [];
  const now = new Date();
  
  for (let i = 29; i >= 0; i--) {
    const date = new Date(now);
    date.setDate(date.getDate() - i);
    
    timeSeries.push({
      date: date.toISOString().split('T')[0],
      activeUsers: Math.floor(metrics.activeUsers * (0.8 + Math.random() * 0.4)),
      documentsProcessed: Math.floor(metrics.documentsProcessed * (0.7 + Math.random() * 0.6)),
      chatMessages: Math.floor(metrics.chatMessages * (0.6 + Math.random() * 0.8)),
      costSavings: Math.floor(metrics.costSavings * (0.5 + Math.random() * 1.0))
    });
  }
  
  // 生成分类数据
  const categories = ['Technology', 'Finance', 'Healthcare', 'Education', 'Retail'];
  const categoryData = categories.map(category => ({
    category,
    value: Math.floor(Math.random() * 1000) + 100,
    growth: Math.random() * 50 - 10 // -10% to +40%
  }));
  
  // 生成性能数据
  const performanceData = [
    { metric: 'Page Load Time', value: metrics.responseTime, target: 500, unit: 'ms' },
    { metric: 'API Response Time', value: Math.random() * 200 + 50, target: 200, unit: 'ms' },
    { metric: 'Uptime', value: 99.95, target: 99.9, unit: '%' },
    { metric: 'Error Rate', value: Math.random() * 0.5, target: 1, unit: '%' }
  ];
  
  return {
    metrics,
    timeSeries,
    categoryData,
    performanceData,
    lastUpdated: new Date().toISOString()
  };
}

/**
 * 生成测试API响应
 */
export function createTestAPIResponse(endpoint: string) {
  const endpointResponses: Record<string, any> = {
    '/api/v1/auth/login': {
      success: true,
      data: {
        token: `test-jwt-token-${Date.now()}`,
        user: {
          id: Math.floor(Math.random() * 1000),
          email: 'test@example.com',
          name: 'Test User',
          role: 'user'
        }
      },
      message: 'Login successful'
    },
    
    '/api/v1/documents': {
      success: true,
      data: {
        documents: Array.from({ length: 10 }, (_, i) => createTestDocumentData()),
        pagination: {
          page: 1,
          limit: 10,
          total: 100,
          pages: 10
        }
      },
      message: 'Documents retrieved successfully'
    },
    
    '/api/v1/chat/messages': {
      success: true,
      data: {
        messages: Array.from({ length: 5 }, (_, i) => createTestChatMessage()),
        conversationId: `conv-${Date.now()}`
      },
      message: 'Messages retrieved successfully'
    },
    
    '/api/v1/cost/estimate': {
      success: true,
      data: createTestCostEstimationData(),
      message: 'Cost estimation completed'
    },
    
    '/api/v1/dashboard/metrics': {
      success: true,
      data: createTestDashboardData(),
      message: 'Dashboard metrics retrieved'
    },
    
    '/api/v1/health': {
      success: true,
      data: {
        status: 'healthy',
        timestamp: new Date().toISOString(),
        version: '1.0.0',
        services: {
          database: 'connected',
          cache: 'connected',
          ai_services: 'available',
          file_storage: 'available'
        }
      },
      message: 'System is healthy'
    }
  };
  
  return endpointResponses[endpoint] || {
    success: true,
    data: {},
    message: 'Request successful'
  };
}

/**
 * 生成测试文件
 */
export function createTestFile(type: string = 'txt') {
  const fileTypes: Record<string, { content: string; mimeType: string }> = {
    txt: {
      content: 'This is a test text file.\nIt contains multiple lines of text for testing purposes.\nEnd of file.',
      mimeType: 'text/plain'
    },
    csv: {
      content: 'Name,Age,Email\nJohn Doe,30,john@example.com\nJane Smith,25,jane@example.com\nBob Johnson,35,bob@example.com',
      mimeType: 'text/csv'
    },
    json: {
      content: JSON.stringify({
        test: true,
        timestamp: new Date().toISOString(),
        data: {
          items: ['item1', 'item2', 'item3'],
          count: 3,
          active: true
        }
      }, null, 2),
      mimeType: 'application/json'
    },
    pdf: {
      content: '%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n4 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 12 Tf\n72 720 Td\n(Test PDF Document) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f\n0000000010 00000 n\n0000000053 00000 n\n0000000106 00000 n\n0000000176 00000 n\ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\nstartxref\n242\n%%EOF',
      mimeType: 'application/pdf'
    }
  };
  
  return fileTypes[type] || fileTypes.txt;
}