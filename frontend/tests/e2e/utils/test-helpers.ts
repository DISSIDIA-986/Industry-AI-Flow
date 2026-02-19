import { expect, BrowserContext, Page } from '@playwright/test';

/**
 * 测试辅助工具函数
 * 提供通用的测试功能和工具
 */

/**
 * 截取页面截图
 */
export async function takeScreenshot(page: Page, name: string) {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const screenshotPath = `test-results/screenshots/${name}-${timestamp}.png`;
  await page.screenshot({ path: screenshotPath, fullPage: true });
  return screenshotPath;
}

/**
 * 记录测试日志
 */
export function logTestStep(step: string, details?: any) {
  const timestamp = new Date().toISOString();
  console.log(`[${timestamp}] ${step}`);
  
  if (details) {
    console.log('详细信息:', JSON.stringify(details, null, 2));
  }
}

/**
 * 模拟网络延迟
 */
export async function simulateNetworkDelay(page: Page, delayMs: number) {
  await page.route('**', async route => {
    await new Promise(resolve => setTimeout(resolve, delayMs));
    await route.continue();
  });
}

/**
 * 模拟API失败
 */
export async function simulateAPIFailure(page: Page, endpointPattern: string) {
  await page.route(endpointPattern, route => route.abort());
}

/**
 * 模拟慢速API响应
 */
export async function simulateSlowAPI(page: Page, endpointPattern: string, delayMs = 2000) {
  await page.route(endpointPattern, async route => {
    await new Promise(resolve => setTimeout(resolve, delayMs));
    await route.continue();
  });
}

/**
 * 模拟空数据响应
 */
export async function simulateEmptyData(page: Page, endpointPattern: string) {
  await page.route(endpointPattern, async route => {
    const response = await route.fetch();
    const json = { data: [], success: true, message: 'No data found' };
    await route.fulfill({ response, json });
  });
}

/**
 * 模拟错误响应
 */
export async function simulateErrorResponse(page: Page, endpointPattern: string, statusCode = 500) {
  await page.route(endpointPattern, async route => {
    await route.fulfill({
      status: statusCode,
      contentType: 'application/json',
      body: JSON.stringify({
        success: false,
        error: 'Internal Server Error',
        message: 'Something went wrong'
      })
    });
  });
}

/**
 * 验证页面性能指标
 */
export async function verifyPerformanceMetrics(page: Page) {
  const metrics = await page.evaluate(() => {
    const timing = performance.timing;
    return {
      loadTime: timing.loadEventEnd - timing.navigationStart,
      domContentLoaded: timing.domContentLoadedEventEnd - timing.navigationStart,
      firstPaint: performance.getEntriesByName('first-paint')[0]?.startTime || 0,
      firstContentfulPaint: performance.getEntriesByName('first-contentful-paint')[0]?.startTime || 0,
      largestContentfulPaint: performance.getEntriesByName('largest-contentful-paint')[0]?.startTime || 0,
      cumulativeLayoutShift: performance.getEntriesByName('layout-shift')[0]?.value || 0
    };
  });

  logTestStep('页面性能指标', metrics);
  
  // 性能断言
  expect(metrics.loadTime).toBeLessThan(3000); // 页面加载时间应小于3秒
  expect(metrics.firstContentfulPaint).toBeLessThan(2000); // FCP应小于2秒
  
  return metrics;
}

/**
 * 验证无障碍性
 */
export async function verifyAccessibility(page: Page) {
  // 检查标题
  const title = await page.title();
  expect(title).toBeTruthy();
  expect(title.length).toBeGreaterThan(0);
  
  // 检查语言属性
  const lang = await page.getAttribute('html', 'lang');
  expect(lang).toBeTruthy();
  
  // 检查图片alt属性
  const imagesWithoutAlt = await page.$$eval('img', imgs => 
    imgs.filter(img => !img.alt).length
  );
  expect(imagesWithoutAlt).toBe(0);
  
  // 检查表单标签
  const formInputsWithoutLabel = await page.$$eval('input, select, textarea', elements =>
    elements.filter(el => {
      const id = el.id;
      const label = document.querySelector(`label[for="${id}"]`);
      return !label && !el.getAttribute('aria-label');
    }).length
  );
  expect(formInputsWithoutLabel).toBe(0);
  
  logTestStep('无障碍性检查通过', {
    title,
    lang,
    imagesWithoutAlt,
    formInputsWithoutLabel
  });
}

/**
 * 验证响应式设计
 */
export async function verifyResponsiveDesign(page: Page) {
  const viewports = [
    { width: 1920, height: 1080, name: 'desktop' },
    { width: 768, height: 1024, name: 'tablet' },
    { width: 375, height: 667, name: 'mobile' }
  ];
  
  for (const viewport of viewports) {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    
    // 检查关键元素在不同视口下是否可见
    const heading = page.getByRole('heading', { name: /Industry AI Flow/i }).first();
    await expect(heading).toBeVisible();
    
    // 截取不同视口的截图
    await takeScreenshot(page, `responsive-${viewport.name}`);
    
    logTestStep(`响应式设计检查 - ${viewport.name}`, viewport);
  }
}

/**
 * 创建测试用户
 */
export async function createTestUser(context: BrowserContext) {
  const testUser = {
    email: `test-${Date.now()}@example.com`,
    password: 'Test123!@#',
    name: 'Test User'
  };
  
  // 这里可以添加创建测试用户的逻辑
  // 例如通过API或数据库操作
  
  return testUser;
}

/**
 * 清理测试数据
 */
export async function cleanupTestData(userEmail: string) {
  // 这里可以添加清理测试数据的逻辑
  // 例如通过API或数据库操作删除测试用户
  logTestStep('清理测试数据', { userEmail });
}

/**
 * 等待元素可见
 */
export async function waitForElement(page: Page, selector: string, timeout = 10000) {
  await page.waitForSelector(selector, { state: 'visible', timeout });
}

/**
 * 等待元素包含文本
 */
export async function waitForText(page: Page, text: string, timeout = 10000) {
  await page.waitForSelector(`:has-text("${text}")`, { state: 'visible', timeout });
}

/**
 * 验证页面URL
 */
export async function verifyPageURL(page: Page, expectedPattern: RegExp | string) {
  if (typeof expectedPattern === 'string') {
    await expect(page).toHaveURL(expectedPattern);
  } else {
    await expect(page).toHaveURL(expectedPattern);
  }
}

/**
 * 验证页面标题
 */
export async function verifyPageTitle(page: Page, expectedTitle: string | RegExp) {
  await expect(page).toHaveTitle(expectedTitle);
}

/**
 * 执行JavaScript代码
 */
export async function executeScript<T>(page: Page, script: string): Promise<T> {
  return await page.evaluate(script);
}

/**
 * 获取控制台错误
 */
export async function getConsoleErrors(page: Page): Promise<string[]> {
  const errors: string[] = [];
  
  page.on('console', msg => {
    if (msg.type() === 'error') {
      errors.push(msg.text());
    }
  });
  
  return errors;
}

/**
 * 验证没有JavaScript错误
 */
export async function verifyNoConsoleErrors(page: Page) {
  const errors = await getConsoleErrors(page);
  expect(errors).toHaveLength(0);
  
  if (errors.length > 0) {
    logTestStep('发现JavaScript错误', errors);
  }
}
