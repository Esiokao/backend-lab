import { expect } from '@playwright/test'

import { signoutViaUi } from '../helpers'

import { test } from '../../fixtures/auth'
test.describe('Shopper Signout journey', () => {
  test('Signout via UI', async ({ freshShopperPage: page }) => {
    // new shopper ctx to prevent infect the shopper.json's login state
    await signoutViaUi(page)

    // guard assertion
    await page.goto('/app/orders')
    await expect(page).toHaveURL(/\/login\?redirect=/)
  })
})
