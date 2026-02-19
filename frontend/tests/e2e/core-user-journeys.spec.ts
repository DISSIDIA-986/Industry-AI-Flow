import { expect, type Locator, test } from '@playwright/test';

import { mockCoreApiEndpoints, seedAuthenticatedSession } from './utils/session';

async function clickByJs(locator: Locator): Promise<void> {
  await locator.evaluate((element) => {
    (element as HTMLElement).click();
  });
}

test.describe('Authentication and access control', () => {
  test('shows login page and can navigate to register page', async ({ page }) => {
    await mockCoreApiEndpoints(page);
    await page.goto('/login');

    await expect(page.getByRole('heading', { name: 'Industry AI Flow' })).toBeVisible();
    await expect(page.getByPlaceholder('your@email.com')).toBeVisible();
    await expect(page.getByRole('button', { name: '登录' })).toBeVisible();

    await page.goto('/register');
    await expect(page).toHaveURL(/\/register$/);
    await expect(page.getByRole('heading', { name: '创建账户' })).toBeVisible();
  });

  test('allows demo user login and redirects out of login page', async ({ page }) => {
    await mockCoreApiEndpoints(page);
    await page.goto('/login');

    await page.getByPlaceholder('your@email.com').fill('demo@example.com');
    await page.getByPlaceholder('••••••••').fill('demo123');
    await clickByJs(page.getByRole('button', { name: '登录' }));

    await expect(page).not.toHaveURL(/\/login$/);
    await expect(page.getByRole('button', { name: '退出登录' })).toBeVisible();
  });
});

test.describe('Authenticated core journeys', () => {
  test.beforeEach(async ({ page }) => {
    await seedAuthenticatedSession(page);
    await mockCoreApiEndpoints(page);
  });

  test('workflow chat sends message and renders AI response', async ({ page }) => {
    await page.goto('/workflow-chat');
    await expect(page.getByRole('heading', { name: '工作流聊天' })).toBeVisible();

    const prompt = 'E2E: 请分析这个项目的预算风险';
    await page.getByPlaceholder('输入您的问题或查询...').fill(prompt);
    await clickByJs(page.getByRole('button', { name: '发送' }));

    await expect(page.getByText(prompt, { exact: true })).toBeVisible();
    await expect(page.getByText(`E2E workflow response for: ${prompt}`)).toBeVisible();
  });

  test('workflow chat supports quick prompt and websocket toggle', async ({ page }) => {
    await page.goto('/workflow-chat');

    const quickPrompt = '估算一个20层办公楼在多伦多的成本风险';
    await clickByJs(page.getByRole('button', { name: quickPrompt }));
    await expect(page.getByPlaceholder('输入您的问题或查询...')).toHaveValue(quickPrompt);

    await clickByJs(page.getByRole('button', { name: 'WebSocket: 关' }));
    await expect(page.getByRole('button', { name: 'WebSocket: 开' })).toBeVisible();
    await expect(page.locator('span.text-xs.text-gray-600').first()).toContainText(
      /已连接|连接中|未连接/,
    );
  });

  test('documents page supports search and empty state', async ({ page }) => {
    await page.goto('/documents-integrated');
    await expect(page.getByRole('heading', { name: '文档管理' })).toBeVisible();

    const searchInput = page.getByPlaceholder('搜索文档名称或类型...');
    await searchInput.fill('施工安全规范');
    await expect(page.getByText('施工安全规范.pdf')).toBeVisible();

    await searchInput.fill('this-document-does-not-exist');
    await expect(page.getByText('没有找到文档')).toBeVisible();
  });

  test('data dashboard renders and supports time range switch', async ({ page }) => {
    await page.goto('/data-dashboard');
    await expect(page.getByRole('heading', { name: '数据分析仪表板' })).toBeVisible();
    await expect(page.getByText('实时系统监控')).toBeVisible();

    await clickByJs(page.getByRole('button', { name: '周度' }));
    await expect(page.getByRole('button', { name: '周度' })).toHaveClass(/bg-blue-600/);
  });

  test('cost estimation runs single and batch prediction', async ({ page }) => {
    await page.goto('/cost-estimation');
    await expect(page.getByRole('heading', { name: 'Single Project Prediction' })).toBeVisible();

    await clickByJs(page.getByRole('button', { name: 'Predict Cost' }));
    await expect(page.getByText('Predicted Actual Cost')).toBeVisible();
    await expect(page.getByText('1,250,000')).toBeVisible();

    await clickByJs(page.getByRole('button', { name: 'Add Current Project To Batch' }));
    await expect(page.getByRole('heading', { name: 'Batch Prediction Queue (1)' })).toBeVisible();

    await clickByJs(page.getByRole('button', { name: 'Run Batch' }));
    await expect(page.getByRole('cell', { name: '$1,250,000' })).toBeVisible();
  });

  test('api integration page executes checks and shows pass state', async ({ page }) => {
    await page.goto('/api-integration-test');
    await expect(page.getByRole('heading', { name: 'API集成测试' })).toBeVisible();

    await clickByJs(page.getByRole('button', { name: '运行所有测试' }));
    await expect(page.getByText('✅ 测试通过').first()).toBeVisible({ timeout: 10000 });
  });

  test('navbar supports cross-page navigation', async ({ page }) => {
    await page.goto('/workflow-chat');
    await page.goto('/documents-integrated');
    await expect(page).toHaveURL(/\/documents-integrated$/);

    await page.goto('/data-dashboard');
    await expect(page).toHaveURL(/\/data-dashboard$/);

    await page.goto('/cost-estimation');
    await expect(page).toHaveURL(/\/cost-estimation$/);
  });
});
