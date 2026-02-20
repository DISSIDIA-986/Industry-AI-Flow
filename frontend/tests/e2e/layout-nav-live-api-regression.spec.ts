import { expect, type Page, test } from '@playwright/test';

import { seedAuthenticatedSession } from './utils/session';

const DESKTOP_VIEWPORT = { width: 1440, height: 900 };

const LIVE_CORE_ROUTES = [
  '/workflow-chat',
  '/documents-integrated',
  '/data-dashboard',
  '/cost-estimation',
] as const;

interface ShellMetrics {
  viewportWidth: number;
  shellMainWidth: number;
  shellMainLeft: number;
  shellRootColumns: string;
}

function topNavbar(page: Page) {
  return page.locator('nav.bg-white.border-b.border-gray-200').first();
}

async function readShellMetrics(page: Page): Promise<ShellMetrics> {
  return page.evaluate(() => {
    const shellMain = document.querySelector('.shell-main-simple, .shell-main');
    if (!(shellMain instanceof HTMLElement)) {
      throw new Error('shell-main or shell-main-simple not found');
    }

    const shellRoot = document.querySelector('.shell-root-simple, .shell-root');
    if (!(shellRoot instanceof HTMLElement)) {
      throw new Error('shell-root or shell-root-simple not found');
    }

    const rect = shellMain.getBoundingClientRect();
    const columns = getComputedStyle(shellRoot).gridTemplateColumns;

    return {
      viewportWidth: window.innerWidth,
      shellMainWidth: rect.width,
      shellMainLeft: rect.left,
      shellRootColumns: columns,
    };
  });
}

test.describe('Live API layout width and navbar persistence regressions', () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize(DESKTOP_VIEWPORT);
    await seedAuthenticatedSession(page);
  });

  test('api diagnostics pages use same-origin backend proxy paths', async ({ page }) => {
    const disallowedBackendUrls: string[] = [];
    page.on('request', (request) => {
      const url = request.url();
      if (url.includes('localhost:8001') || url.includes('localhost:8002')) {
        disallowedBackendUrls.push(url);
      }
    });

    await page.goto('/api-test');
    await expect(page.getByText('Backend address: /api/backend/api/v1 (Same origin proxy)')).toBeVisible();
    await expect(topNavbar(page)).toBeVisible();

    const healthProxyResponse = page.waitForResponse(
      (response) =>
        response.request().method() === 'GET' &&
        response.url().includes('/api/backend/api/v1/health'),
    );

    const healthRow = page
      .locator('div.border.border-gray-200.rounded-lg.p-4')
      .filter({ hasText: 'GET /health' })
      .first();
    await healthRow.getByRole('button', { name: 'test' }).click();
    await expect((await healthProxyResponse).status()).toBe(200);

    await page.goto('/api-integration-test');
    await expect(page.getByText('APIaddress: /api/backend/api/v1 (Same origin proxy)')).toBeVisible();
    expect(
      disallowedBackendUrls,
      `browser should not call hardcoded backend hosts: ${disallowedBackendUrls.join(', ')}`,
    ).toEqual([]);
  });

  test('workflow page health probe shows connected backend status', async ({ page }) => {
    const healthResponsePromise = page.waitForResponse(
      (response) =>
        response.request().method() === 'GET' &&
        response.url().includes('/api/backend/api/v1/health'),
    );

    await page.goto('/workflow-chat');

    const healthResponse = await healthResponsePromise;
    expect(healthResponse.status()).toBe(200);

    await expect(topNavbar(page)).toBeVisible();
    await expect(page.getByRole('button', { name: 'Log out' })).toBeVisible();
    await expect(page.getByText('APIConnected')).toBeVisible({ timeout: 15000 });
  });

  test('desktop layout keeps main content wide across live routes', async ({ page }) => {
    for (const route of LIVE_CORE_ROUTES) {
      await test.step(`live layout check: ${route}`, async () => {
        await page.goto(route);
        await expect(topNavbar(page)).toBeVisible();
        await expect(page.getByRole('button', { name: 'Log out' })).toBeVisible();

        const metrics = await readShellMetrics(page);
        const widthRatio = metrics.shellMainWidth / metrics.viewportWidth;

        expect(
          widthRatio,
          `${route} shell-main width ratio should stay above 60%, got ${widthRatio.toFixed(3)}`,
        ).toBeGreaterThan(0.6);
        expect(
          metrics.shellMainWidth,
          `${route} shell-main width should not collapse to narrow column`,
        ).toBeGreaterThan(860);
        expect(
          metrics.shellRootColumns,
          `${route} shell-root should not reserve a fixed 280px sidebar track`,
        ).not.toContain('280px');
        expect(metrics.shellMainLeft, `${route} shell-main should stay onscreen`).toBeGreaterThanOrEqual(0);
      });
    }
  });

  test('top navbar remains visible after live cross-page navigation', async ({ page }) => {
    await page.goto('/workflow-chat');
    await expect(topNavbar(page)).toBeVisible();
    await expect(page.getByRole('button', { name: 'Log out' })).toBeVisible();

    const navFlow = [
      { label: 'Document management', url: /\/documents-integrated$/ },
      { label: 'Data dashboard', url: /\/data-dashboard$/ },
      { label: 'cost estimate', url: /\/cost-estimation$/ },
      { label: 'Workflow chat', url: /\/workflow-chat$/ },
    ] as const;

    for (const step of navFlow) {
      await test.step(`navigate via navbar (live): ${step.label}`, async () => {
        await page.getByRole('link', { name: step.label }).click();
        await expect(page).toHaveURL(step.url);
        await expect(topNavbar(page)).toBeVisible();
        await expect(page.getByRole('link', { name: 'Industry AI Flow' })).toBeVisible();
        await expect(page.getByRole('button', { name: 'Log out' })).toBeVisible();
      });
    }
  });

  test('cost prediction succeeds for bearer session without jwt secret requirement', async ({ page }) => {
    await page.goto('/cost-estimation');
    await expect(topNavbar(page)).toBeVisible();
    await expect(page.getByRole('button', { name: 'Log out' })).toBeVisible();

    const predictResponsePromise = page.waitForResponse(
      (response) =>
        response.request().method() === 'POST' &&
        response.url().includes('/api/backend/api/v1/cost-estimation/predict'),
    );

    await page.getByRole('button', { name: 'Predict Cost' }).click();

    const predictResponse = await predictResponsePromise;
    expect(predictResponse.status()).toBe(200);

    const payload = (await predictResponse.json()) as { success?: boolean };
    expect(payload.success).toBe(true);

    await expect(page.getByText('Predicted Actual Cost')).toBeVisible({ timeout: 15000 });
    await expect(page.getByText(/AUTH_JWT_SECRET not configured/i)).toHaveCount(0);
    await expect(page.getByText(/User authentication required/i)).toHaveCount(0);
  });
});
