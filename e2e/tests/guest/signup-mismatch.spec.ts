import { test, expect } from '@playwright/test'

import { PASSWORD, uniqueEmail } from '../helpers'

test.describe('Signup with mismatched passwords', () => {
  test('shows an error when the password and confirm password do not match', async ({
    page
  }) => {
    const email = uniqueEmail('mismatch')

    await page.goto('/login')
    await page.getByRole('button', { name: 'Sign up' }).click()
    await page.getByLabel('Name', { exact: true }).fill('E2E Dup')
    await page.getByLabel('Email', { exact: true }).fill(email)
    await page.getByLabel('Password', { exact: true }).fill(PASSWORD)
    await page
      .getByRole('textbox', { name: 'Confirm password', exact: true })
      .fill('wrong-password')
    await page.getByRole('button', { name: 'Create account' }).click()

    await expect(
      page.getByText('Passwords do not match.', { exact: true })
    ).toBeVisible()
  })
})
