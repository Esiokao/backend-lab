import { ref } from "vue";

import { api } from "@/lib/api";
import { CartSchema, type Cart, type CartItem } from "@/lib/schemas";

// 購物車 store（v1.7）：對接後端 /cart 系列（持久化於 cart_items 表）。
// v1.8：勾選式結帳 —— selected 記錄勾選的商品（session 內狀態，重整後預設全選）；
// checkout(product_ids) 只結帳選中品，其餘留車（後端支援）。

const items = ref<CartItem[]>([]);
const total = ref<string | number>("0");
const loaded = ref(false);
const busy = ref(false);

// 勾選狀態：product_id → 是否選中。新出現的商品預設選中；移除的自動清掉。
const selected = ref<Record<number, boolean>>({});

const count = () => items.value.reduce((n, item) => n + item.quantity, 0);

const isSelected = (productId: number) => !!selected.value[productId];

// 撞庫存（quantity > stock 或零庫存）→ 不可勾選結帳。
const isSelectable = (item: CartItem) => item.stock >= item.quantity;
const selectedItems = () =>
  items.value.filter((item) => selected.value[item.product_id] && isSelectable(item));
const selectedCount = () => selectedItems().reduce((n, item) => n + item.quantity, 0);
const selectedTotal = () =>
  selectedItems().reduce((sum, item) => sum + Number(item.subtotal), 0);
const allSelected = () =>
  items.value.length > 0 && items.value.every((item) => selected.value[item.product_id]);

function toggleSelect(productId: number): void {
  selected.value = { ...selected.value, [productId]: !selected.value[productId] };
}

function toggleAll(): void {
  const next = !allSelected();
  const record: Record<number, boolean> = {};
  for (const item of items.value) record[item.product_id] = next;
  selected.value = record;
}

function apply(cart: Cart): void {
  items.value = cart.items;
  total.value = cart.total;
  loaded.value = true;

  const previous = selected.value;
  const record: Record<number, boolean> = {};
  for (const item of cart.items) {
    // 預設全選，但撞庫存的品項自動取消（庫存恢復後 re-fetch 會重新預設選中）。
    record[item.product_id] = (previous[item.product_id] ?? true) && isSelectable(item);
  }
  selected.value = record;
}

async function refresh(): Promise<void> {
  try {
    apply(await api.get("/cart", CartSchema));
  } catch {
    // 未登入（401）或暫時失敗：保持現狀，不打擾使用者。
  }
}

async function add(productId: number, quantity: number): Promise<void> {
  busy.value = true;
  try {
    apply(await api.post("/cart/items", { product_id: productId, quantity }, CartSchema));
  } finally {
    busy.value = false;
  }
}

async function updateQty(productId: number, quantity: number): Promise<void> {
  busy.value = true;
  try {
    apply(await api.patch(`/cart/items/${productId}`, { quantity }, CartSchema));
  } finally {
    busy.value = false;
  }
}

async function remove(productId: number): Promise<void> {
  busy.value = true;
  try {
    apply(await api.delete(`/cart/items/${productId}`, CartSchema));
  } finally {
    busy.value = false;
  }
}

async function clear(): Promise<void> {
  busy.value = true;
  try {
    apply(await api.delete("/cart", CartSchema));
  } finally {
    busy.value = false;
  }
}

type CheckedOutOrder = { id: number };

// 結帳：帶 product_ids 只結選中品（undefined = 整台車）；成功後重抓剩餘車況。
async function checkout(productIds?: number[]): Promise<CheckedOutOrder> {
  busy.value = true;
  try {
    const order = await api.post<CheckedOutOrder>(
      "/cart/checkout",
      productIds === undefined ? undefined : { product_ids: productIds },
    );
    await refresh();
    return order;
  } finally {
    busy.value = false;
  }
}

export function useCart() {
  return {
    items,
    total,
    loaded,
    busy,
    selected,
    count,
    isSelected,
    isSelectable,
    selectedItems,
    selectedCount,
    selectedTotal,
    allSelected,
    toggleSelect,
    toggleAll,
    refresh,
    add,
    updateQty,
    remove,
    clear,
    checkout,
  };
}
