import { execSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { expect, type Page } from '@playwright/test'

// repo 根目錄（本檔在 e2e/tests/）：compose.yaml 在這一層。
// 相對 cwd 會隨「從哪裡呼叫 playwright」而變——從 repo 根跑時 cwd:'..' 指向
// C:\Projects，compose.yaml 找不到，限流清不掉且不報錯 → flaky 回歸。
// 錨定檔案自己的位置（同 auth.setup.ts 的慣例），從哪裡跑都正確。
const ROOT = fileURLToPath(new URL('../../', import.meta.url))

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
  // 註冊成功後前端會自動登入（打 /login）——跟 loginViaUi 一樣要先清限流，
  // 否則整批跑時 setup/auth/store 的登入擠進同一個 60s 窗口就撞 429。
  clearRateLimit()

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
    { cwd: ROOT, stdio: 'pipe' }
  )
    .toString()
    .trim()
    .split('\n')
    .filter(Boolean)

  if (out.length > 0) {
    execSync(`docker compose exec -T redis redis-cli DEL ${out.join(' ')}`, {
      cwd: ROOT,
      stdio: 'pipe'
    })
  }
}
