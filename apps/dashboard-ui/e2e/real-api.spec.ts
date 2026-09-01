import { expect, test } from '@playwright/test'

test.skip(!process.env.REAL_API_E2E, 'requires the real API integration environment')

test('registers and signs in through the real API and SQLite database', async ({ page, request }) => {
  const email = `real-e2e-${Date.now()}@securitytest.io`
  const password = 'SecurePassword123'
  const registration = await request.post('http://127.0.0.1:8000/auth/register', {
    data: {
      email,
      password,
      full_name: 'Real Stack Operator',
      organization: 'Quality Engineering',
    },
  })
  expect(registration.status()).toBe(201)

  await page.goto('/login')
  await page.getByLabel('Email').fill(email)
  await page.locator('#login-password').fill(password)
  await page.getByRole('button', { name: /sign in/i }).click()

  await expect(page).toHaveURL(/\/dashboard$/)
  await expect(page.getByText(email)).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Threat Dashboard' })).toBeVisible()
  await expect.poll(() => page.evaluate(() => localStorage.getItem('access_token'))).not.toBeNull()
})
