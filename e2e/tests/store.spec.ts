import { expect, test } from "@playwright/test";

import { signupViaUi, uniqueEmail } from "./helpers";

// 旅程 2：逛店 → 加購物車 → 購物車頁看得到商品。
// 點「第一張有 Add to cart 的卡片」是合法的模糊——任何在庫商品都符合目的。

test("add to cart shows the product in the cart", async ({ page }) => {
  const email = uniqueEmail("e2e-cart");
  await signupViaUi(page, "E2E Cart", email);

  await page.goto("/");

  // 挑一張有「Add to cart」的卡片（缺貨卡是 Out of stock — notify me，不會被選到）。
  const card = page
    .locator(".product-card", {
      has: page.getByRole("button", { name: "Add to cart" }),
    })
    .first();
  const productName = await card.locator(".product-name").innerText();

  await card.getByRole("button", { name: "Add to cart" }).click();

  // header 的購物車連結進購物車頁（footer 也有一個「Cart」文字連結，
  // 用 aria-label 鎖定 header 那顆）。
  await page.locator('a[aria-label="Cart"]').click();

  await expect(page.getByText(productName).first()).toBeVisible();
  await expect(page.getByText("Your cart is empty")).toBeHidden();
});
