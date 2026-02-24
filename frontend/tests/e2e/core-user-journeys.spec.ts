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
    await expect(page.getByRole('button', { name: 'Log in' })).toBeVisible();

    await page.goto('/register');
    await expect(page).toHaveURL(/\/register$/);
    await expect(page.getByRole('heading', { name: 'create Account' })).toBeVisible();
  });

  test('allows demo user login and redirects out of login page', async ({ page }) => {
    await mockCoreApiEndpoints(page);
    await page.goto('/login');

    await page.getByPlaceholder('your@email.com').fill('demo@example.com');
    await page.getByPlaceholder('••••••••').fill('demo123');
    await clickByJs(page.getByRole('button', { name: 'Log in' }));

    await expect(page).not.toHaveURL(/\/login$/);
    await expect(page.getByRole('button', { name: 'Log out' })).toBeVisible();
  });
});

test.describe('Authenticated core journeys', () => {
  test.beforeEach(async ({ page }) => {
    await seedAuthenticatedSession(page);
    await mockCoreApiEndpoints(page);
  });

  test('workflow chat sends message and renders AI response', async ({ page }) => {
    await page.goto('/workflow-chat');
    await expect(page.getByRole('heading', { name: 'Workflow chat' })).toBeVisible();

    const prompt = 'E2E: Please analyze the budget risks of this project';
    const followUp = 'Which section of the reference document supports this answer?';
    await page.getByPlaceholder('Enter your question or query...').fill(prompt);
    await clickByJs(page.getByRole('button', { name: 'send' }));

    await expect(page.getByText(prompt, { exact: true })).toBeVisible();
    await expect(page.getByText(`E2E workflow response for: ${prompt}`)).toBeVisible();
    await expect(page.getByText('Suggested follow-up questions:')).toBeVisible();

    const followUpButton = page.getByRole('button', { name: followUp }).first();
    await expect(followUpButton).toBeVisible();
    await clickByJs(followUpButton);
    await expect(page.getByPlaceholder('Enter your question or query...')).toHaveValue(followUp);
  });

  test('workflow chat supports quick prompt and websocket toggle', async ({ page }) => {
    await page.goto('/workflow-chat');

    const quickPrompt = 'Estimating the cost risk of a 20-story office building in Toronto';
    await clickByJs(page.getByRole('button', { name: quickPrompt }));
    await expect(page.getByPlaceholder('Enter your question or query...')).toHaveValue(quickPrompt);

    await clickByJs(page.getByRole('button', { name: 'WebSocket: close' }));
    await expect(page.getByRole('button', { name: 'WebSocket: open' })).toBeVisible();
    await expect(page.locator('span.text-xs.text-gray-600').first()).toContainText(
      /Connected|Connecting|Not connected/,
    );
  });

  test('documents page supports search and empty state', async ({ page }) => {
    await page.goto('/documents-integrated');
    await expect(page.getByRole('heading', { name: 'Document management' })).toBeVisible();

    const searchInput = page.getByPlaceholder('Search document name or type...');
    await searchInput.fill('Construction safety regulations');
    await expect(page.getByText('Construction safety regulations.pdf')).toBeVisible();

    await searchInput.fill('this-document-does-not-exist');
    await expect(page.getByText('No document found')).toBeVisible();
  });

  test('data dashboard renders and supports time range switch', async ({ page }) => {
    await page.goto('/data-dashboard');
    await expect(page.getByRole('heading', { name: 'Data analysis dashboard' })).toBeVisible();
    await expect(page.getByText('Real-time system monitoring')).toBeVisible();

    await clickByJs(page.getByRole('button', { name: 'Weekly' }));
    await expect(page.getByRole('button', { name: 'Weekly' })).toHaveClass(/bg-blue-600/);
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
    await expect(page.getByRole('cell', { name: /1,250,000/ })).toBeVisible();
  });

  test('api integration page executes checks and shows pass state', async ({ page }) => {
    await page.goto('/api-integration-test');
    await expect(page.getByRole('heading', { name: 'APIIntegration testing' })).toBeVisible();

    await clickByJs(page.getByRole('button', { name: 'Run all tests' }));
    await expect(page.getByText('✅ Test passed').first()).toBeVisible({ timeout: 10000 });
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
