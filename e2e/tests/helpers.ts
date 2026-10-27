import { expect, type Page } from "@playwright/test";

// 每條測試的資料獨立：email 帶隨機後綴，避免測試間互相污染。
export function uniqueEmail(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.floor(Math.random() * 1000)}@e2e.example.com`;
}

const PASSWORD = "Sup3rSecret!";

export async function signupViaUi(
  page: Page,
  name: string,
  email: string,
): Promise<void> {
  await page.goto("/login");
  await page.getByRole("button", { name: "Sign up" }).click();
  await page.getByLabel("Name", { exact: true }).fill(name);
  await page.getByLabel("Email", { exact: true }).fill(email);
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByRole("button", { name: "Create account" }).click();

  // 註冊成功 → 自動登入：header 出現帳號選單。
  await expect(page.getByRole("button", { name: "Account menu" })).toBeVisible();
}

export async function loginViaUi(page: Page, email: string): Promise<void> {
  await page.goto("/login");
  await page.getByLabel("Email", { exact: true }).fill(email);
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("button", { name: "Account menu" })).toBeVisible();
}

export async function signoutViaUi(page: Page): Promise<void> {
  await page.getByRole("button", { name: "Account menu" }).click();
  await page.getByRole("menuitem", { name: "Sign out" }).click();
  await expect(page.getByRole("button", { name: "Account menu" })).toBeHidden();
}

export { PASSWORD };
