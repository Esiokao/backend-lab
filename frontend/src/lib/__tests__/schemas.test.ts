import { describe, expect, it } from "vitest";

import {
  CartSchema,
  LoginFormSchema,
  PasswordFormSchema,
  ProductFormSchema,
  ProductSchema,
  SignupFormSchema,
} from "../schemas";

// zod schemas：API 契約閘門與表單驗證的單一真相（後端 Pydantic 的鏡像）。
// 這裡鎖的是「契約形狀」——後端改壞欄位時，這裡先紅。

describe("LoginFormSchema", () => {
  it("accepts valid credentials", () => {
    const result = LoginFormSchema.safeParse({ email: "a@a.com", password: "secret" });
    expect(result.success).toBe(true);
  });

  it("rejects malformed email with the issue on the email path", () => {
    const result = LoginFormSchema.safeParse({ email: "not-an-email", password: "x" });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues[0].path).toContain("email");
    }
  });

  it("rejects empty password", () => {
    const result = LoginFormSchema.safeParse({ email: "a@a.com", password: "" });
    expect(result.success).toBe(false);
  });
});

describe("SignupFormSchema", () => {
  it("accepts a full valid signup", () => {
    const result = SignupFormSchema.safeParse({
      name: "Ada",
      email: "ada@example.com",
      password: "12345678",
    });
    expect(result.success).toBe(true);
  });

  it("enforces the 8-character password floor", () => {
    const result = SignupFormSchema.safeParse({
      name: "Ada",
      email: "ada@example.com",
      password: "1234567",
    });
    expect(result.success).toBe(false);
  });

  it("rejects a blank name", () => {
    const result = SignupFormSchema.safeParse({ name: "  ", email: "a@a.com", password: "12345678" });
    expect(result.success).toBe(false);
  });
});

describe("PasswordFormSchema", () => {
  it("flags mismatched confirmation on the confirm path", () => {
    const result = PasswordFormSchema.safeParse({ next: "12345678", confirm: "12345679" });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues[0].path).toContain("confirm");
    }
  });

  it("accepts matching passwords", () => {
    expect(
      PasswordFormSchema.safeParse({ next: "12345678", confirm: "12345678" }).success,
    ).toBe(true);
  });
});

describe("ProductFormSchema", () => {
  it("coerces numeric strings from the form inputs", () => {
    const result = ProductFormSchema.safeParse({
      name: "Beans",
      description: "",
      image_url: "",
      price: "12.5",
      stock: "3",
    });
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.price).toBe(12.5);
      expect(result.data.stock).toBe(3);
    }
  });

  it("rejects negative price", () => {
    const result = ProductFormSchema.safeParse({
      name: "Beans",
      description: "",
      image_url: "",
      price: "-1",
      stock: "3",
    });
    expect(result.success).toBe(false);
  });

  it("rejects fractional stock", () => {
    const result = ProductFormSchema.safeParse({
      name: "Beans",
      description: "",
      image_url: "",
      price: "1",
      stock: "2.5",
    });
    expect(result.success).toBe(false);
  });
});

describe("ProductSchema (API contract)", () => {
  it("normalizes Decimal-as-string price into a number", () => {
    const result = ProductSchema.safeParse({
      id: 1,
      name: "Sweater",
      description: null,
      image_url: null,
      price: "100.00",
      stock: 12,
      category_id: null,
      created_at: "2026-10-24T00:00:00Z",
      is_active: true,
    });
    expect(result.success).toBe(true);
    if (result.success) expect(result.data.price).toBe(100);
  });

  it("fails when a field is missing", () => {
    const result = ProductSchema.safeParse({ id: 1, name: "Sweater" });
    expect(result.success).toBe(false);
  });
});

describe("CartSchema (API contract)", () => {
  const validItem = {
    product_id: 1,
    product_name: "Sweater",
    quantity: 2,
    unit_price: "89.00",
    subtotal: "178.00",
    stock: 12,
  };

  it("accepts a well-formed cart and converts totals to numbers", () => {
    const result = CartSchema.safeParse({ items: [validItem], total: "178.00" });
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.items[0].subtotal).toBe(178);
      expect(result.data.total).toBe(178);
    }
  });

  it("fails when the stock field is absent — the selection logic depends on it", () => {
    const { stock: _omit, ...withoutStock } = validItem;
    const result = CartSchema.safeParse({ items: [withoutStock], total: "0" });
    expect(result.success).toBe(false);
  });
});
