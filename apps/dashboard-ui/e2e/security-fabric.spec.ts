import { expect, Page, test } from '@playwright/test'

const user = {
  id: 1,
  email: 'operator@example.com',
  full_name: 'Security Operator',
  organization: 'Example Security',
  is_active: true,
}

const alert = {
  id: 7,
  threat_id: 'threat-007',
  severity: 'critical',
  status: 'open',
  classification: 'Command & Control',
  source_ip: '10.0.0.7',
  destination_ip: '192.168.1.4',
  confidence_score: 0.94,
  description: 'Known command-and-control traffic pattern.',
  created_at: '2026-08-31T12:00:00Z',
}

async function mockApi(page: Page, options: { loginFails?: boolean } = {}) {
  await page.route('http://localhost:8000/**', async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    const path = url.pathname

    if (path === '/auth/token' && request.method() === 'POST') {
      return options.loginFails
        ? route.fulfill({ status: 401, json: { detail: 'Invalid credentials' } })
        : route.fulfill({ json: { access_token: 'test-token', token_type: 'bearer' } })
    }
    if (path === '/auth/token' && request.method() === 'DELETE') {
      return route.fulfill({ status: 204, body: '' })
    }
    if (path === '/auth/register') return route.fulfill({ status: 201, json: user })
    if (path === '/auth/me') return route.fulfill({ json: user })
    if (path === '/alerts/stats') {
      return route.fulfill({ json: { total: 1, open: 1, critical: 1, high: 0, medium: 0, low: 0 } })
    }
    if (path === '/alerts/export') {
      return route.fulfill({
        contentType: 'text/csv',
        headers: { 'Content-Disposition': 'attachment; filename="alerts.csv"' },
        body: 'id,severity,status\n7,critical,open\n',
      })
    }
    if (/^\/alerts\/\d+\/(acknowledge|resolve)$/.test(path)) {
      return route.fulfill({ json: { ...alert, status: path.endsWith('resolve') ? 'resolved' : 'acknowledged' } })
    }
    if (path === '/alerts') return route.fulfill({ json: [alert] })
    if (path === '/payments/status') return route.fulfill({ json: { plan: 'free', active: true } })
    return route.fulfill({ status: 404, json: { detail: 'Not mocked' } })
  })
}

async function openAuthenticated(page: Page, path = '/dashboard') {
  await mockApi(page)
  await page.goto('/login')
  await page.evaluate(() => localStorage.setItem('access_token', 'test-token'))
  await page.goto(path)
}

test('redirects an anonymous user to sign in', async ({ page }) => {
  await page.goto('/dashboard')
  await expect(page).toHaveURL(/\/login$/)
  await expect(page.getByRole('heading', { name: 'Sign in' })).toBeVisible()
})

test('toggles password visibility accessibly', async ({ page }) => {
  await page.goto('/login')
  const password = page.locator('#login-password')
  await expect(password).toHaveAttribute('type', 'password')
  await page.getByRole('button', { name: 'Show password' }).click()
  await expect(password).toHaveAttribute('type', 'text')
})

test('shows a stable error for invalid credentials', async ({ page }) => {
  await mockApi(page, { loginFails: true })
  await page.goto('/login')
  await page.getByLabel('Email').fill('wrong@example.com')
  await page.locator('#login-password').fill('wrong-password')
  await page.getByRole('button', { name: /sign in/i }).click()
  await expect(page.getByText('Invalid credentials. Check your email and password.')).toBeVisible()
})

test('signs in and opens the threat dashboard', async ({ page }) => {
  await mockApi(page)
  await page.goto('/login')
  await page.getByLabel('Email').fill(user.email)
  await page.locator('#login-password').fill('correct-password')
  await page.getByRole('button', { name: /sign in/i }).click()
  await expect(page).toHaveURL(/\/dashboard$/)
  await expect(page.getByRole('heading', { name: 'Threat Dashboard' })).toBeVisible()
  await expect.poll(() => page.evaluate(() => localStorage.getItem('access_token'))).toBe('test-token')
})

test('restores a saved session through the profile endpoint', async ({ page }) => {
  await openAuthenticated(page)
  await expect(page.getByText(user.email)).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Threat Dashboard' })).toBeVisible()
})

test('signs out and clears the local session', async ({ page }) => {
  await openAuthenticated(page)
  await page.getByRole('button', { name: 'Sign out' }).click()
  await expect(page).toHaveURL(/\/login$/)
  await expect.poll(() => page.evaluate(() => localStorage.getItem('access_token'))).toBeNull()
})

test('renders alerts returned by the API', async ({ page }) => {
  await openAuthenticated(page, '/alerts')
  await expect(page.getByText('Command & Control')).toBeVisible()
  await expect(page.getByText('94%')).toBeVisible()
})

test('applies the critical-severity query filter', async ({ page }) => {
  await openAuthenticated(page, '/alerts')
  const requestPromise = page.waitForRequest((request) =>
    request.url().includes('/alerts?') && request.url().includes('severity=critical'))
  await page.getByRole('button', { name: /Critical \(1\)/ }).click()
  const request = await requestPromise
  expect(new URL(request.url()).searchParams.get('severity')).toBe('critical')
})

test('acknowledges an open alert and confirms the action', async ({ page }) => {
  await openAuthenticated(page, '/alerts')
  await page.getByTitle('Acknowledge').click()
  await expect(page.getByText('Alert acknowledged')).toBeVisible()
})

test('resolves an open alert and confirms the action', async ({ page }) => {
  await openAuthenticated(page, '/alerts')
  await page.getByTitle('Resolve').click()
  await expect(page.getByText('Alert resolved')).toBeVisible()
})

test('downloads the current alert set as CSV', async ({ page }) => {
  await openAuthenticated(page, '/alerts')
  const downloadPromise = page.waitForEvent('download')
  await page.getByRole('button', { name: /Export CSV/ }).click()
  const download = await downloadPromise
  expect(download.suggestedFilename()).toMatch(/^alerts-\d{4}-\d{2}-\d{2}\.csv$/)
})

test('shows a not-found page for an unknown route', async ({ page }) => {
  await page.goto('/not-a-real-route')
  await expect(page.getByText('404')).toBeVisible()
})
