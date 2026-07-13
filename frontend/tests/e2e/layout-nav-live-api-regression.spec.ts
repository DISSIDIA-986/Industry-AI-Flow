import { expect, type Page, test } from '@playwright/test';

import { seedAuthenticatedSession } from './utils/session';

const DESKTOP_VIEWPORT = { width: 1440, height: 900 };

const LIVE_CORE_ROUTES = [
  '/workflow-chat',
  '/documents-integrated',
  '/overview',
  '/cost-estimation',
] as const;

interface ShellMetrics {
  viewportWidth: number;
  shellMainWidth: number;
  shellMainLeft: number;
}

function topNavbar(page: Page) {
  return page.locator('nav.bg-white.border-b.border-gray-200').first();
}

async function readShellMetrics(page: Page): Promise<ShellMetrics> {
  return page.evaluate(() => {
    // The (mvp) layout was simplified to a full-width <main> — the old
    // .shell-root/.shell-main grid + sidebar was removed — so measure <main>
    // to assert the content area stays wide. No sidebar grid remains to collapse.
    const shellMain = document.querySelector('main');
    if (!(shellMain instanceof HTMLElement)) {
      throw new Error('main content element not found');
    }

    const rect = shellMain.getBoundingClientRect();

    return {
      viewportWidth: window.innerWidth,
      shellMainWidth: rect.width,
      shellMainLeft: rect.left,
    };
  });
}

test.describe('Live API layout width and navbar persistence regressions', () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize(DESKTOP_VIEWPORT);
    await seedAuthenticatedSession(page);
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
    // The header status indicator is a colored dot + the bare status word
    // (no "API" label prefix anymore), so match the exact "Connected" text.
    await expect(page.getByText('Connected', { exact: true })).toBeVisible({
      timeout: 15000,
    });
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
          `${route} main width should not collapse to narrow column`,
        ).toBeGreaterThan(860);
        expect(metrics.shellMainLeft, `${route} main should stay onscreen`).toBeGreaterThanOrEqual(0);
      });
    }
  });

  test('top navbar remains visible after live cross-page navigation', async ({ page }) => {
    await page.goto('/workflow-chat');
    await expect(topNavbar(page)).toBeVisible();
    await expect(page.getByRole('button', { name: 'Log out' })).toBeVisible();

    // Labels must match the current flat navbar (src/components/Navbar.tsx);
    // the old pre-redesign labels no longer resolve.
    const navFlow = [
      { label: 'Documents', url: /\/documents-integrated$/ },
      { label: 'Intent Demo', url: /\/intent-demo$/ },
      { label: 'Cost Estimation', url: /\/cost-estimation$/ },
      { label: 'Workflow Chat', url: /\/workflow-chat$/ },
    ] as const;

    for (const step of navFlow) {
      await test.step(`navigate via navbar (live): ${step.label}`, async () => {
        await page.getByRole('link', { name: step.label }).click();
        // Live routes hit the real backend and dev-mode compiles the target
        // page on first visit, so a client-side transition can exceed the 5s
        // default. Give the URL assertion the same 15s budget the other live
        // assertions use.
        await expect(page).toHaveURL(step.url, { timeout: 15000 });
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
