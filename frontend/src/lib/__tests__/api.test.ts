import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, SchemaError } from "../api";
import { CartSchema } from "../schemas";

// api client：契約閘門的行為——ok 直通、錯誤轉 ApiError、schema 不合丟 SchemaError。
// fetch 以 stub 取代（模組在全域 fetch 上運作）。

function stubFetch(response: Response | { status: number; body: unknown }): void {
  const raw =
    response instanceof Response
      ? response
      : new Response(JSON.stringify(response.body), {
          status: response.status,
          headers: { "Content-Type": "application/json" },
        });
  vi.stubGlobal("fetch", vi.fn(async () => raw));
}

beforeEach(() => {
  vi.unstubAllGlobals();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("api.get", () => {
  it("returns parsed JSON on success", async () => {
    stubFetch({ status: 200, body: { items: [], total: "0" } });
    const { api } = await import("../api");
    const data = await api.get("/cart");
    expect(data).toEqual({ items: [], total: "0" });
  });

  it("throws ApiError carrying the detail from the error body", async () => {
    stubFetch({ status: 409, body: { detail: "Insufficient product stock: 2" } });
    const { api } = await import("../api");
    const err = await api.get("/cart").catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).status).toBe(409);
    expect((err as ApiError).message).toBe("Insufficient product stock: 2");
  });

  it("validates the response against the schema and normalizes decimals", async () => {
    stubFetch({
      status: 200,
      body: {
        items: [
          {
            product_id: 1,
            product_name: "Sweater",
            quantity: 2,
            unit_price: "89.00",
            subtotal: "178.00",
            stock: 12,
          },
        ],
        total: "178.00",
      },
    });
    const { api } = await import("../api");
    const cart = await api.get("/cart", CartSchema);
    expect(cart.items[0].subtotal).toBe(178);
  });

  it("throws SchemaError naming the offending field when the contract breaks", async () => {
    // 後端若漏掉 stock 欄位：當場炸在這裡，而不是默默讓勾選邏輯拿到 undefined。
    stubFetch({
      status: 200,
      body: { items: [{ product_id: 1, product_name: "Sweater", quantity: 2 }], total: "0" },
    });
    const { api } = await import("../api");
    const err = await api.get("/cart", CartSchema).catch((e: unknown) => e);
    expect(err).toBeInstanceOf(SchemaError);
    expect((err as SchemaError).issues).toContain("stock");
  });
});
