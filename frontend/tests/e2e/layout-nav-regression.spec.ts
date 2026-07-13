import { expect, type Page, test } from '@playwright/test';

import { mockCoreApiEndpoints, seedAuthenticatedSession } from './utils/session';

const DESKTOP_VIEWPORT = { width: 1440, height: 900 };

const CORE_ROUTES = [
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
          `${route} main width should not collapse to narrow column`,
        ).toBeGreaterThan(860);
        expect(metrics.shellMainLeft, `${route} main should stay onscreen`).toBeGreaterThanOrEqual(0);
      });
    }
  });

  test('top navbar remains visible and functional after cross-page navigation', async ({ page }) => {
    await page.goto('/workflow-chat');
    await expect(topNavbar(page)).toBeVisible();
    await expect(page.getByRole('button', { name: 'Log out' })).toBeVisible();

    // Labels must match the current flat navbar (src/components/Navbar.tsx).
    // The old 'Document management' / 'cost estimate' / 'Workflow chat' labels
    // predate the navbar redesign and no longer resolve.
    const navFlow = [
      { label: 'Documents', url: /\/documents-integrated$/ },
      { label: 'Intent Demo', url: /\/intent-demo$/ },
      { label: 'Cost Estimation', url: /\/cost-estimation$/ },
      { label: 'Workflow Chat', url: /\/workflow-chat$/ },
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
