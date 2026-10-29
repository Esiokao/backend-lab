import { execSync } from 'node:child_process'
import { expect, type Page } from '@playwright/test'

// 每條測試的資料獨立：email 帶隨機後綴，避免測試間互相污染。
export function uniqueEmail(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.floor(Math.random() * 1000)}@e2e.example.com`
}

const PASSWORD = 'Sup3rSecret!'

export async function signupViaUi(
  page: Page,
  name: string,
  email: string
): Promise<void> {
  await page.goto('/login')
  await page.getByRole('button', { name: 'Sign up' }).click()
  await page.getByLabel('Name', { exact: true }).fill(name)
  await page.getByLabel('Email', { exact: true }).fill(email)
  await page.getByLabel('Password', { exact: true }).fill(PASSWORD)
  await page.getByRole('button', { name: 'Create account' }).click()

  // 註冊成功 → 自動登入：header 出現帳號選單。
  await expect(page.getByRole('button', { name: 'Account menu' })).toBeVisible()
}

export async function loginViaUi(page: Page, email: string): Promise<void> {
  clearRateLimit()
  await page.goto('/login')
  await page.getByLabel('Email', { exact: true }).fill(email)
  await page.getByLabel('Password', { exact: true }).fill(PASSWORD)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page.getByRole('button', { name: 'Account menu' })).toBeVisible()
}

export async function signoutViaUi(page: Page): Promise<void> {
  // handleLogout 有 window.confirm —— Playwright 預設 dismiss（= 取消登出），
  // 必須先掛 accept，否則登出永遠靜默失敗。
  page.once('dialog', (dialog) => dialog.accept())

  await page.getByRole('button', { name: 'Account menu' }).click()
  await page.getByRole('menuitem', { name: 'Sign out' }).click()
  await expect(page.getByRole('button', { name: 'Account menu' })).toBeHidden()
}

export { PASSWORD }

// 登入限流是 5 次/60 秒（per IP）— E2E 從同一個 localhost 連發，一定撞牆。
// 每次走 UI 登入前清掉 rate_limit keys（跟 pytest conftest 的做法同概念）。
export function clearRateLimit(): void {
  const out = execSync(
    'docker compose exec -T redis redis-cli --scan --pattern "rate_limit:*"',
    { cwd: '..', stdio: 'pipe' }
  )
    .toString()
    .trim()
    .split('\n')
    .filter(Boolean)

  if (out.length > 0) {
    execSync(`docker compose exec -T redis redis-cli DEL ${out.join(' ')}`, {
      cwd: '..',
      stdio: 'pipe'
    })
  }
}
