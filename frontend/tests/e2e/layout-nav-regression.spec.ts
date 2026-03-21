import { expect, type Page, test } from '@playwright/test';

import { mockCoreApiEndpoints, seedAuthenticatedSession } from './utils/session';

const DESKTOP_VIEWPORT = { width: 1440, height: 900 };

const CORE_ROUTES = [
  '/workflow-chat',
  '/documents-integrated',
  '/data-dashboard',
  '/cost-estimation',
  '/api-integration-test',
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

test.describe('Layout width and navbar persistence regressions', () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize(DESKTOP_VIEWPORT);
    await seedAuthenticatedSession(page);
    await mockCoreApiEndpoints(page);
  });

  test('desktop layout keeps main content wide across core pages', async ({ page }) => {
    for (const route of CORE_ROUTES) {
      await test.step(`layout check: ${route}`, async () => {
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

  test('top navbar remains visible and functional after cross-page navigation', async ({ page }) => {
    await page.goto('/workflow-chat');
    await expect(topNavbar(page)).toBeVisible();
    await expect(page.getByRole('button', { name: 'Log out' })).toBeVisible();

    const navFlow = [
      { label: 'APItest', url: /\/api-integration-test$/ },
      { label: 'Document management', url: /\/documents-integrated$/ },
      { label: 'System Overview', url: /\/data-dashboard$/ },
      { label: 'cost estimate', url: /\/cost-estimation$/ },
      { label: 'Workflow chat', url: /\/workflow-chat$/ },
    ] as const;

    for (const step of navFlow) {
      await test.step(`navigate via navbar: ${step.label}`, async () => {
        await page.getByRole('link', { name: step.label }).click();
        await expect(page).toHaveURL(step.url);
        await expect(topNavbar(page)).toBeVisible();
        await expect(page.getByRole('link', { name: 'Industry AI Flow' })).toBeVisible();
        await expect(page.getByRole('button', { name: 'Log out' })).toBeVisible();
      });
    }
  });
});
