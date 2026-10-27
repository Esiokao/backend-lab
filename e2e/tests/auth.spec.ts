import { expect, test } from "@playwright/test";

import { loginViaUi, signoutViaUi, signupViaUi, uniqueEmail } from "./helpers";

// 旅程 1：註冊 → 自動登入 → 登出 → 登入（含 Keep me signed in）。
// 這條是所有需要登入的旅程的地基，也鎖住 remember-me 的 UI 行為。

test("signup auto-logs in, sign out, sign back in with keep-me-signed-in", async ({
  page,
}) => {
  const email = uniqueEmail("e2e-auth");

  await signupViaUi(page, "E2E Auth", email);
  await signoutViaUi(page);

  await loginViaUi(page, email);

  // Keep me signed in：勾選後登入同樣成功（30 分鐘 vs 7 天的差別在 cookie，UI 不顯現）。
  await signoutViaUi(page);
  await page.goto("/login");
  await page.getByLabel("Email", { exact: true }).fill(email);
  await page.getByLabel("Password", { exact: true }).fill("Sup3rSecret!");
  await page.getByLabel(/Keep me signed in/).check();
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("button", { name: "Account menu" })).toBeVisible();
});
