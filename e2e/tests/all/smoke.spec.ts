// tests/smoke.spec.ts
import { expect, test } from '@playwright/test'

test.describe('Smoke', () => {
  test('storefront loads', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('heading', { name: 'Store' })).toBeVisible()
  })
})
