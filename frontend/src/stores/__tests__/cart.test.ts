import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Cart } from "@/lib/schemas";

// cart store：勾選與庫存可選性的核心邏輯（v1.8/v1.10 的行為鎖）。
// api 以 mock 取代；模組級 ref 狀態用 resetModules 每測重置。

vi.mock("@/lib/api", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

import { api } from "@/lib/api";

type CartApi = {
  useCart: () => {
    items: { value: Cart["items"] };
    isSelected: (id: number) => boolean;
    isSelectable: (item: Cart["items"][number]) => boolean;
    selectedItems: () => Cart["items"];
    selectedCount: () => number;
    selectedTotal: () => number;
    allSelected: () => boolean;
    toggleSelect: (id: number) => void;
    toggleAll: () => void;
    refresh: () => Promise<void>;
    updateQty: (id: number, qty: number) => Promise<void>;
    checkout: (ids?: number[]) => Promise<{ id: number }>;
  };
};

async function freshCart(): Promise<ReturnType<CartApi["useCart"]>> {
  vi.resetModules();
  const mod = (await import("../cart")) as unknown as CartApi;
  return mod.useCart();
}

function sweater(qty = 1, stock = 12) {
  return {
    product_id: 1,
    product_name: "Sweater",
    quantity: qty,
    unit_price: 89,
    subtotal: 89 * qty,
    stock,
  };
}

function mug(qty = 1, stock = 40) {
  return {
    product_id: 2,
    product_name: "Mug",
    quantity: qty,
    unit_price: 34,
    subtotal: 34 * qty,
    stock,
  };
}

beforeEach(() => {
  vi.mocked(api.get).mockReset();
  vi.mocked(api.post).mockReset();
  vi.mocked(api.patch).mockReset();
});

describe("selection defaults", () => {
  it("selects every item on first load", async () => {
    vi.mocked(api.get).mockResolvedValue({ items: [sweater(), mug()], total: 123 });
    const cart = await freshCart();
    await cart.refresh();

    expect(cart.isSelected(1)).toBe(true);
    expect(cart.isSelected(2)).toBe(true);
    expect(cart.allSelected()).toBe(true);
    expect(cart.selectedCount()).toBe(2);
  });

  it("auto-deselects items whose quantity exceeds stock", async () => {
    vi.mocked(api.get).mockResolvedValue({ items: [sweater(3, 2), mug()], total: 301 });
    const cart = await freshCart();
    await cart.refresh();

    expect(cart.isSelectable({ ...sweater(3, 2) })).toBe(false);
    expect(cart.isSelected(1)).toBe(false);
    expect(cart.isSelected(2)).toBe(true);
    expect(cart.selectedTotal()).toBe(34); // 只有 Mug 可選
  });

  it("treats zero-stock items as unselectable", async () => {
    const outOfStock = sweater(1, 0);
    expect((await freshCart()).isSelectable(outOfStock)).toBe(false);
  });
});

describe("selection interactions", () => {
  it("toggleSelect flips a single item and totals follow", async () => {
    vi.mocked(api.get).mockResolvedValue({ items: [sweater(), mug()], total: 123 });
    const cart = await freshCart();
    await cart.refresh();

    cart.toggleSelect(1);
    expect(cart.isSelected(1)).toBe(false);
    expect(cart.selectedTotal()).toBe(34);

    cart.toggleSelect(1);
    expect(cart.selectedTotal()).toBe(123);
  });

  it("toggleAll clears then restores the whole selection", async () => {
    vi.mocked(api.get).mockResolvedValue({ items: [sweater(), mug()], total: 123 });
    const cart = await freshCart();
    await cart.refresh();

    cart.toggleAll();
    expect(cart.allSelected()).toBe(false);
    expect(cart.selectedCount()).toBe(0);

    cart.toggleAll();
    expect(cart.allSelected()).toBe(true);
  });

  it("keeps manual deselection across refreshes of the same items", async () => {
    vi.mocked(api.get).mockResolvedValue({ items: [sweater(), mug()], total: 123 });
    const cart = await freshCart();
    await cart.refresh();
    cart.toggleSelect(1);

    await cart.refresh();
    expect(cart.isSelected(1)).toBe(false);
    expect(cart.isSelected(2)).toBe(true);
  });

  it("reselects restored stock on a fresh page load (default-on)", async () => {
    // 使用者手動取消 → 重整頁面（模組重載）→ 回預設全選。
    vi.mocked(api.get).mockResolvedValue({ items: [sweater(), mug()], total: 123 });
    const cart = await freshCart();
    await cart.refresh();
    cart.toggleSelect(1);

    const reloaded = await freshCart();
    await reloaded.refresh();
    expect(reloaded.isSelected(1)).toBe(true);
  });
});

describe("mutations", () => {
  it("updateQty keeps selection for surviving items and prunes removed ones", async () => {
    vi.mocked(api.get).mockResolvedValueOnce({ items: [sweater(), mug()], total: 123 });
    const cart = await freshCart();
    await cart.refresh();

    vi.mocked(api.patch).mockResolvedValue({ items: [sweater(2)], total: 178 }); // Mug 被移除
    await cart.updateQty(2, 0).catch(() => undefined);

    expect(cart.isSelected(1)).toBe(true);
    expect(cart.selectedItems().some((item) => item.product_id === 2)).toBe(false);
  });

  it("checkout sends only the selected product ids and refreshes the cart", async () => {
    vi.mocked(api.get).mockResolvedValue({ items: [sweater(), mug()], total: 123 });
    const cart = await freshCart();
    await cart.refresh();
    cart.toggleSelect(2);

    vi.mocked(api.post).mockResolvedValue({ id: 64 });
    vi.mocked(api.get).mockResolvedValue({ items: [], total: 0 });
    const order = await cart.checkout([1]);

    expect(order.id).toBe(64);
    expect(api.post).toHaveBeenCalledWith("/cart/checkout", { product_ids: [1] });
    expect(cart.items.value).toHaveLength(0);
  });

  it("checkout without ids posts no body (whole cart)", async () => {
    vi.mocked(api.get).mockResolvedValue({ items: [sweater()], total: 89 });
    const cart = await freshCart();
    await cart.refresh();

    vi.mocked(api.post).mockResolvedValue({ id: 65 });
    await cart.checkout();

    expect(api.post).toHaveBeenCalledWith("/cart/checkout", undefined);
  });
});
