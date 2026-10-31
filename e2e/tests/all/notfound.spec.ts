import { expect, test } from '@playwright/test'

// 旅程 3：未知路徑 → 404 頁（catch-all → NotFoundView）。

test.describe('NotFound', () => {
  test('unknown route shows the 404 page with a way home', async ({ page }) => {
    await page.goto('/definitely-not-a-real-page')

    await expect(
      page.getByRole('heading', { name: 'Page not found' })
    ).toBeVisible()

    // 出口存在：回店面（header/footer 都有同名連結，取第一個）。
    await page.getByRole('link', { name: 'Back to storefront' }).first().click()
    await expect(page).toHaveURL(/\/$/)
  })
})
