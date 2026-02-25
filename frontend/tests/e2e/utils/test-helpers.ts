import { expect, BrowserContext, Page } from '@playwright/test';

/**
 * Test helper functions
 * Provide common testing functions and tools
 */

/**
 * Take a screenshot of the page
 */
export async function takeScreenshot(page: Page, name: string) {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const screenshotPath = `test-results/screenshots/${name}-${timestamp}.png`;
  await page.screenshot({ path: screenshotPath, fullPage: true });
  return screenshotPath;
}

/**
 * Record test log
 */
export function logTestStep(step: string, details?: any) {
  const timestamp = new Date().toISOString();
  console.log(`[${timestamp}] ${step}`);
  
  if (details) {
    console.log('Details:', JSON.stringify(details, null, 2));
  }
}

/**
 * Simulate network latency
 */
export async function simulateNetworkDelay(page: Page, delayMs: number) {
  await page.route('**', async route => {
    await new Promise(resolve => setTimeout(resolve, delayMs));
    await route.continue();
  });
}

/**
 * simulationAPIfail
 */
export async function simulateAPIFailure(page: Page, endpointPattern: string) {
  await page.route(endpointPattern, route => route.abort());
}

/**
 * Simulate slow speedAPIresponse
 */
export async function simulateSlowAPI(page: Page, endpointPattern: string, delayMs = 2000) {
  await page.route(endpointPattern, async route => {
    await new Promise(resolve => setTimeout(resolve, delayMs));
    await route.continue();
  });
}

/**
 * Simulate empty data response
 */
export async function simulateEmptyData(page: Page, endpointPattern: string) {
  await page.route(endpointPattern, async route => {
    const response = await route.fetch();
    const json = { data: [], success: true, message: 'No data found' };
    await route.fulfill({ response, json });
  });
}

/**
 * Simulate error response
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
 * Verify page performance metrics
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

  logTestStep('Page performance metrics', metrics);
  
  // Performance assertions
  expect(metrics.loadTime).toBeLessThan(3000); // Page load time should be less than 3 seconds
  expect(metrics.firstContentfulPaint).toBeLessThan(2000); // FCPShould be less than 2 seconds
  
  return metrics;
}

/**
 * Verify accessibility
 */
export async function verifyAccessibility(page: Page) {
  // Check title
  const title = await page.title();
  expect(title).toBeTruthy();
  expect(title.length).toBeGreaterThan(0);
  
  // Check language properties
  const lang = await page.getAttribute('html', 'lang');
  expect(lang).toBeTruthy();
  
  // Check picturesaltproperty
  const imagesWithoutAlt = await page.$$eval('img', imgs => 
    imgs.filter(img => !img.alt).length
  );
  expect(imagesWithoutAlt).toBe(0);
  
  // Check form tags
  const formInputsWithoutLabel = await page.$$eval('input, select, textarea', elements =>
    elements.filter(el => {
      const id = el.id;
      const label = document.querySelector(`label[for="${id}"]`);
      return !label && !el.getAttribute('aria-label');
    }).length
  );
  expect(formInputsWithoutLabel).toBe(0);
  
  logTestStep('Accessibility check passed', {
    title,
    lang,
    imagesWithoutAlt,
    formInputsWithoutLabel
  });
}

/**
 * Validate responsive design
 */
export async function verifyResponsiveDesign(page: Page) {
  const viewports = [
    { width: 1920, height: 1080, name: 'desktop' },
    { width: 768, height: 1024, name: 'tablet' },
    { width: 375, height: 667, name: 'mobile' }
  ];
  
  for (const viewport of viewports) {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    
    // Check whether key elements are visible in different viewports
    const heading = page.getByRole('heading', { name: /Industry AI Flow/i }).first();
    await expect(heading).toBeVisible();
    
    // Take screenshots of different viewports
    await takeScreenshot(page, `responsive-${viewport.name}`);
    
    logTestStep(`Responsive design check - ${viewport.name}`, viewport);
  }
}

/**
 * Create test user
 */
export async function createTestUser(context: BrowserContext) {
  const testUser = {
    email: `test-${Date.now()}@example.com`,
    password: 'Test123!@#',
    name: 'Test User'
  };
  
  // Here you can add logic to create test users
  // For example viaAPIor database operations
  
  return testUser;
}

/**
 * Clean test data
 */
export async function cleanupTestData(userEmail: string) {
  // Here you can add logic to clean test data
  // For example viaAPIOr database operation to delete the test user
  logTestStep('Clean test data', { userEmail });
}

/**
 * Wait for element to be visible
 */
export async function waitForElement(page: Page, selector: string, timeout = 10000) {
  await page.waitForSelector(selector, { state: 'visible', timeout });
}

/**
 * Wait for element to contain text
 */
export async function waitForText(page: Page, text: string, timeout = 10000) {
  await page.waitForSelector(`:has-text("${text}")`, { state: 'visible', timeout });
}

/**
 * Verification pageURL
 */
export async function verifyPageURL(page: Page, expectedPattern: RegExp | string) {
  if (typeof expectedPattern === 'string') {
    await expect(page).toHaveURL(expectedPattern);
  } else {
    await expect(page).toHaveURL(expectedPattern);
  }
}

/**
 * Verify page title
 */
export async function verifyPageTitle(page: Page, expectedTitle: string | RegExp) {
  await expect(page).toHaveTitle(expectedTitle);
}

/**
 * implementJavaScriptcode
 */
export async function executeScript<T>(page: Page, script: string): Promise<T> {
  return await page.evaluate(script);
}

/**
 * Get console error
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
 * Verify noJavaScriptmistake
 */
export async function verifyNoConsoleErrors(page: Page) {
  const errors = await getConsoleErrors(page);
  expect(errors).toHaveLength(0);
  
  if (errors.length > 0) {
    logTestStep('DiscoverJavaScriptmistake', errors);
  }
}
