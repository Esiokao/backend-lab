import { execSync } from 'node:child_process'
import { mkdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

import { test as setup, expect } from '@playwright/test'

import { uniqueEmail, PASSWORD } from './helpers'

const ADMIN_EMAIL = 'admin@e2e.example.com'

// repo 根目錄（本檔在 e2e/tests/）：compose.yaml 在這一層。
// 不用相對 cwd —— 相對路徑會隨「從哪裡呼叫 playwright」而變，Windows 上已經炸過一次。
const ROOT = fileURLToPath(new URL('../../', import.meta.url))

// compose.yaml 在根目錄 → 不需要 -f；SQL 一律從 stdin 餵（避免 Windows 引號地獄）。
const PSQL = 'docker compose exec -T postgres psql -U admin -d backend_lab'

setup.describe('Setup', () => {
  // ① 種商品目錄：冪等（WHERE NOT EXISTS），SQL 直接 stdin 餵給 psql。
  setup('seed catalog products', async () => {
    execSync(PSQL, {
      cwd: ROOT,
      input: `
INSERT INTO products (name, description, price, stock, is_active)
SELECT 'E2E Widget A', 'Seeded product for e2e journeys', 10.00, 50, true
WHERE NOT EXISTS (SELECT 1 FROM products WHERE name = 'E2E Widget A');

INSERT INTO products (name, description, price, stock, is_active)
SELECT 'E2E Widget B', 'Seeded product for e2e journeys', 20.00, 0, true
WHERE NOT EXISTS (SELECT 1 FROM products WHERE name = 'E2E Widget B');`,
      stdio: ['pipe', 'pipe', 'pipe']
    })
  })

  // ② shopper storageState：走 UI 註冊流程（順便當註冊功能的煙霧測試）。
  setup('create shopper storage state', async ({ page }) => {
    const email = uniqueEmail('shopper')
    await page.goto('/login')
    await page.getByRole('button', { name: 'Sign up' }).click()
    await page.getByLabel('Name', { exact: true }).fill('E2E Shopper')
    await page.getByLabel('Email', { exact: true }).fill(email)
    await page.getByLabel('Password', { exact: true }).fill(PASSWORD)
    await page.getByRole('button', { name: 'Create account' }).click()
    await expect(
      page.getByRole('button', { name: 'Account menu' })
    ).toBeVisible()

    mkdirSync('.auth', { recursive: true })
    await page.context().storageState({ path: '.auth/shopper.json' })
  })

  // ③ admin storageState：API 建帳（重跑 409 = 已存在，無妨）→ psql 升級 → UI 登入。
  setup('create admin storage state', async ({ page, request }) => {
    await request.post('/api/users', {
      data: { name: 'E2E Admin', email: ADMIN_EMAIL, password: PASSWORD }
    })

    // 升級為 admin：API 沒有 bootstrap 端點（PRD §5.2 缺口），
    // 走 compose 裡的 postgres 直改 —— e2e 的 README 有記錄此慣例。
    execSync(PSQL, {
      cwd: ROOT,
      input: `UPDATE users SET role='admin' WHERE email='${ADMIN_EMAIL}';`,
      stdio: ['pipe', 'pipe', 'pipe']
    })

    await page.goto('/login')
    await page.getByLabel('Email', { exact: true }).fill(ADMIN_EMAIL)
    await page.getByLabel('Password', { exact: true }).fill(PASSWORD)
    await page.getByRole('button', { name: 'Sign in' }).click()
    await expect(
      page.getByRole('button', { name: 'Account menu' })
    ).toBeVisible()

    mkdirSync('.auth', { recursive: true })
    await page.context().storageState({ path: '.auth/admin.json' })
  })
})
