import { ref } from "vue";

import { api } from "@/lib/api";

// 購物車 store（v1.7）：對接後端 /cart 系列（持久化於 cart_items 表）。
// 登入時 refresh；未登入不打 API（store 保持空，badge 隱藏）。

export type CartItem = {
  product_id: number;
  product_name: string;
  quantity: number;
  unit_price: string | number;
  subtotal: string | number;
};

export type Cart = {
  items: CartItem[];
  total: string | number;
};

const items = ref<CartItem[]>([]);
const total = ref<string | number>("0");
const loaded = ref(false);
const busy = ref(false);

const count = () => items.value.reduce((n, item) => n + item.quantity, 0);

function apply(cart: Cart): void {
  items.value = cart.items;
  total.value = cart.total;
  loaded.value = true;
}

async function refresh(): Promise<void> {
  try {
    apply(await api.get<Cart>("/cart"));
  } catch {
    // 未登入（401）或暫時失敗：保持現狀，不打擾使用者。
  }
}

async function add(productId: number, quantity: number): Promise<void> {
  busy.value = true;
  try {
    apply(await api.post<Cart>("/cart/items", { product_id: productId, quantity }));
  } finally {
    busy.value = false;
  }
}

async function updateQty(productId: number, quantity: number): Promise<void> {
  busy.value = true;
  try {
    apply(await api.patch<Cart>(`/cart/items/${productId}`, { quantity }));
  } finally {
    busy.value = false;
  }
}

async function remove(productId: number): Promise<void> {
  busy.value = true;
  try {
    apply(await api.delete<Cart>(`/cart/items/${productId}`));
  } finally {
    busy.value = false;
  }
}

async function clear(): Promise<void> {
  busy.value = true;
  try {
    apply(await api.delete<Cart>("/cart"));
  } finally {
    busy.value = false;
  }
}

type CheckedOutOrder = { id: number };

async function checkout(): Promise<CheckedOutOrder> {
  busy.value = true;
  try {
    const order = await api.post<CheckedOutOrder>("/cart/checkout");
    apply({ items: [], total: "0" });
    return order;
  } finally {
    busy.value = false;
  }
}

export function useCart() {
  return { items, total, loaded, busy, count, refresh, add, updateQty, remove, clear, checkout };
}
