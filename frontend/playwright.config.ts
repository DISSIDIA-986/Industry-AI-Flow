import { defineConfig, devices } from '@playwright/test';

const isCI = !!process.env.CI;
const runCrossBrowser = process.env.PW_CROSS_BROWSER === '1';
const frontendHost = process.env.PW_FRONTEND_HOST || '127.0.0.1';
const frontendPort = process.env.PW_FRONTEND_PORT || '3123';
const frontendBaseUrl = `http://${frontendHost}:${frontendPort}`;

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: isCI,
  retries: isCI ? 2 : 0,
  workers: isCI ? 1 : undefined,
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['json', { outputFile: 'playwright-results.json' }],
    ['junit', { outputFile: 'junit-results.xml' }],
    ['list']
  ],
  use: {
    baseURL: frontendBaseUrl,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: runCrossBrowser
    ? [
        { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
        { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
        { name: 'webkit', use: { ...devices['Desktop Safari'] } },
      ]
    : [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: `npm run dev -- --hostname ${frontendHost} --port ${frontendPort}`,
    url: `${frontendBaseUrl}/login`,
    reuseExistingServer: !isCI,
    timeout: 120 * 1000,
  },
});
