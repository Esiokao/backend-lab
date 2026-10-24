<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import Icon from "@/components/Icon.vue";
import { ApiError } from "@/lib/api";
import { useCart } from "@/stores/cart";
import { useToast } from "@/stores/toast";

// 購物車（v1.7）：GET /cart 列表、PATCH/DELETE items、checkout → 訂單詳情接 pay。
// 庫存上限在結帳時由後端把關（409 → 友善 toast）；數量上限 100 為 API 契約。

const router = useRouter();
const toast = useToast();
const { items, total, busy, refresh, updateQty, remove, clear, checkout } = useCart();

const loading = ref(true);
const checkingOut = ref(false);

function formatPrice(price: string | number): string {
  return `$${Number(price).toFixed(2)}`;
}

async function setQty(productId: number, quantity: number): Promise<void> {
  if (quantity < 1) return; // 移除請用 ×
  if (quantity > 100) {
    toast.show("Quantity cannot exceed 100.");
    return;
  }
  try {
    await updateQty(productId, quantity);
  } catch (err) {
    toast.show(err instanceof ApiError ? `Update failed: ${err.message}` : "Update failed.");
  }
}

async function step(productId: number, current: number, delta: number): Promise<void> {
  await setQty(productId, current + delta);
}

async function onQtyInput(productId: number, current: number, event: Event): Promise<void> {
  const value = Number((event.target as HTMLInputElement).value);
  if (Number.isInteger(value) && value >= 1 && value <= 100 && value !== current) {
    await setQty(productId, value);
  } else {
    // 還原輸入框（re-render 由 store 狀態驅動）。
    (event.target as HTMLInputElement).value = String(current);
  }
}

async function removeItem(productId: number, name: string): Promise<void> {
  try {
    await remove(productId);
    toast.show(`Removed "${name}".`);
  } catch (err) {
    toast.show(err instanceof ApiError ? `Remove failed: ${err.message}` : "Remove failed.");
  }
}

async function clearCart(): Promise<void> {
  if (!window.confirm("Clear all items from your cart?")) return;
  try {
    await clear();
    toast.show("Cart cleared.");
  } catch (err) {
    toast.show(err instanceof ApiError ? `Clear failed: ${err.message}` : "Clear failed.");
  }
}

async function doCheckout(): Promise<void> {
  checkingOut.value = true;
  try {
    const order = await checkout();
    toast.show(`Order #${order.id} created.`);
    // 直達訂單詳情：下一步就是 Pay now。
    await router.push({ name: "order-detail", params: { id: order.id } });
  } catch (err) {
    // 庫存不足等後端 409 → 原因轉友善文案。
    if (err instanceof ApiError && err.message.startsWith("Insufficient product stock:")) {
      const id = Number(err.message.split(":").pop());
      const item = items.value.find((entry) => entry.product_id === id);
      toast.show(
        item
          ? `Not enough stock for "${item.product_name}" (only ${item.quantity} reserved).`
          : "Not enough stock for an item in your cart.",
      );
    } else {
      toast.show(err instanceof ApiError ? `Checkout failed: ${err.message}` : "Checkout failed.");
    }
  } finally {
    checkingOut.value = false;
  }
}

onMounted(async () => {
  await refresh();
  loading.value = false;
});
</script>

<template>
  <section class="page-heading">
    <div class="th-main">
      <h1>Cart</h1>
      <p>Review your items, then checkout to place the order.</p>
    </div>
    <router-link :to="{ name: 'storefront' }" class="text-button">
      <Icon name="arrow" :size="15" /> Continue shopping
    </router-link>
    <div class="th-cell"><small>Sheet</small><b>CART-01</b></div>
  </section>

  <p v-if="loading" class="empty-state">Loading cart...</p>

  <template v-else-if="items.length > 0">
    <section class="data-panel">
      <div class="panel-header">
        <div>
          <h2>Items</h2>
          <p>{{ items.length }} product{{ items.length === 1 ? "" : "s" }} in your cart.</p>
        </div>
        <button type="button" class="ghost-button" :disabled="busy" @click="clearCart">
          Clear cart
        </button>
      </div>
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Product</th>
              <th>Unit price</th>
              <th>Qty</th>
              <th>Subtotal</th>
              <th><span class="sr-only">Actions</span></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in items" :key="item.product_id">
              <td><strong>{{ item.product_name }}</strong></td>
              <td><span class="order-total">{{ formatPrice(item.unit_price) }}</span></td>
              <td>
                <div class="qty-stepper">
                  <button
                    type="button"
                    :aria-label="`Decrease ${item.product_name}`"
                    :disabled="busy || item.quantity <= 1"
                    @click="step(item.product_id, item.quantity, -1)"
                  >
                    −
                  </button>
                  <input
                    type="number"
                    min="1"
                    max="100"
                    :value="item.quantity"
                    :aria-label="`${item.product_name} quantity`"
                    @change="onQtyInput(item.product_id, item.quantity, $event)"
                  />
                  <button
                    type="button"
                    :aria-label="`Increase ${item.product_name}`"
                    :disabled="busy || item.quantity >= 100"
                    @click="step(item.product_id, item.quantity, 1)"
                  >
                    +
                  </button>
                </div>
              </td>
              <td><span class="order-total">{{ formatPrice(item.subtotal) }}</span></td>
              <td>
                <button
                  type="button"
                  class="row-action row-delete"
                  :aria-label="`Remove ${item.product_name}`"
                  :disabled="busy"
                  @click="removeItem(item.product_id, item.product_name)"
                >
                  <Icon name="close" :size="14" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="data-panel cart-summary">
      <div class="panel-header">
        <div>
          <h2>Total</h2>
          <p>Stock is reserved at checkout.</p>
        </div>
        <span class="cart-total">{{ formatPrice(total) }}</span>
      </div>
      <div class="cart-summary-actions">
        <button
          type="button"
          class="primary-button"
          :disabled="busy || checkingOut"
          @click="doCheckout"
        >
          <Icon name="bolt" :size="15" />
          {{ checkingOut ? "Checking out..." : "Checkout" }}
        </button>
      </div>
    </section>
  </template>

  <section v-else class="data-panel">
    <div class="panel-header">
      <div>
        <h2>Your cart is empty</h2>
        <p>Browse the catalog and add something you like.</p>
      </div>
    </div>
    <div class="cart-empty-actions">
      <router-link :to="{ name: 'storefront' }" class="primary-button">
        <Icon name="cart" :size="15" /> Browse catalog
      </router-link>
    </div>
  </section>
</template>
