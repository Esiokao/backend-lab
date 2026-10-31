import { expect, test } from '@playwright/test'
import { uniqueEmail, PASSWORD } from '../helpers'

test.describe('Duplicate signup', () => {
  test('shows an error when the email is already registered', async ({
    page,
    request
  }) => {
    // ── ① 造資料：一個已存在的帳號（API 造，不走 UI）──
    // request fixture 自動帶 config 的 baseURL，直接相對路徑。
    const email = uniqueEmail('dup')
    const res = await request.post('/api/users', {
      data: { name: 'E2E Dup', email, password: PASSWORD }
    })
    expect(res.status(), await res.text()).toBe(200)

    // ── ② 動作：用同一個 email 走 UI 註冊 ──
    await page.goto('/login')
    await page.getByRole('button', { name: 'Sign up' }).click()
    await page.getByLabel('Name', { exact: true }).fill('E2E Dup')
    await page.getByLabel('Email', { exact: true }).fill(email)
    await page.getByLabel('Password', { exact: true }).fill(PASSWORD)
    await page.getByRole('button', { name: 'Create account' }).click()

    // ── ③ 驗證 ──
    // 正向：錯誤 banner 出現，內容是前端翻譯過的那句（regex 容錯）
    await expect(page.getByRole('alert')).toContainText(/already registered/i)

    // 反向：沒有登入成功——帳號選單不存在
    await expect(
      page.getByRole('button', { name: 'Account menu' })
    ).toBeHidden()
  })
})
