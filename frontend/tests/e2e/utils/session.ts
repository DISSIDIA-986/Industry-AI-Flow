import { Page } from '@playwright/test';

const E2E_USER = {
  id: 'e2e-user',
  name: 'E2E User',
  email: 'e2e@example.com',
  roles: ['user'],
};

export async function seedAuthenticatedSession(page: Page): Promise<void> {
  await page.addInitScript((user) => {
    const token = 'e2e-token';
    localStorage.setItem('industry-aiflow-token', token);
    localStorage.setItem('industry-aiflow-user', JSON.stringify(user));
    localStorage.setItem('token', token);
    localStorage.setItem('user', JSON.stringify(user));
    localStorage.setItem('userId', user.id);
  }, E2E_USER);
}

export async function mockCoreApiEndpoints(page: Page): Promise<void> {
  await page.route('**/api/v1/health', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'ok',
        memory_usage_mb: 256,
        docker_available: false,
        version: 'e2e',
        tenant: 'public',
      }),
    });
  });

  await page.route('**/api/v1/auth/login', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        token: 'e2e-token',
        user: E2E_USER,
      }),
    });
  });

  await page.route('**/api/v1/auth/register', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        token: 'e2e-token',
        user: E2E_USER,
      }),
    });
  });

  await page.route('**/api/v1/auth/logout', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ success: true }),
    });
  });

  await page.route('**/api/v1/query', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'query-e2e',
        query: 'E2E query',
        response: 'E2E query response',
        timestamp: new Date().toISOString(),
        confidence: 0.99,
      }),
    });
  });

  await page.route('**/api/v1/workflow/query', async (route) => {
    const payload = route.request().postDataJSON() as { query?: string } | null;
    const query = payload?.query ?? 'E2E query';
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'workflow-e2e',
        query,
        response: `E2E workflow response for: ${query}`,
        intent: {
          type: 'cost_estimation',
          confidence: 0.92,
          description: '成本估算查询',
        },
        sources: [
          {
            document_id: 'doc-e2e-1',
            document_name: 'E2E-Document.pdf',
            relevance: 0.88,
            content: 'E2E source snippet',
          },
        ],
        timestamp: new Date().toISOString(),
        confidence: 0.96,
      }),
    });
  });

  await page.route('**/api/v1/documents', async (route) => {
    if (route.request().method().toUpperCase() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      });
      return;
    }

    await route.continue();
  });

  await page.route('**/api/v1/cost-estimation/predict', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        prediction: {
          predicted_actual_cost_cad: 1250000,
          predicted_cost_overrun_pct: 8.75,
          prediction_interval_cad: {
            lower: 1180000,
            upper: 1330000,
          },
        },
      }),
    });
  });

  await page.route('**/api/v1/cost-estimation/predict-batch', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        predictions: [
          {
            predicted_actual_cost_cad: 1250000,
            predicted_cost_overrun_pct: 8.75,
            prediction_interval_cad: {
              lower: 1180000,
              upper: 1330000,
            },
          },
        ],
      }),
    });
  });
}
