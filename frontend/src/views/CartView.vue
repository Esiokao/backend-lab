<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import Icon from "@/components/Icon.vue";
import StorefrontHeader from "@/components/StorefrontHeader.vue";
import StorefrontFooter from "@/components/StorefrontFooter.vue";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/stores/auth";
import { useCart } from "@/stores/cart";
import { useToast } from "@/stores/toast";

// 購物車（v1.8）：勾選式 —— 單選/全選，只結帳選中品；
// Checkout → /checkout 付款頁（明細 → 付款 → 結果頁）。

const router = useRouter();
const toast = useToast();
const { user } = useAuth();
const {
  items,
  total,
  busy,
  isSelected,
  isSelectable,
  selectedItems,
  selectedCount,
  selectedTotal,
  allSelected,
  toggleSelect,
  toggleAll,
  refresh,
  updateQty,
  remove,
  clear,
} = useCart();

const loading = ref(true);

function formatPrice(price: string | number): string {
  return `$${Number(price).toFixed(2)}`;
}

async function setQty(productId: number, quantity: number, stock?: number): Promise<void> {
  if (quantity < 1) return; // 移除請用 ×
  if (quantity > 100) {
    toast.show("Quantity cannot exceed 100.");
    return;
  }
  if (stock !== undefined && quantity > stock) {
    toast.show(`Only ${stock} in stock.`);
    return;
  }
  try {
    await updateQty(productId, quantity);
  } catch (err) {
    toast.show(err instanceof ApiError ? `Update failed: ${err.message}` : "Update failed.");
  }
}

async function step(
  productId: number,
  current: number,
  delta: number,
  stock?: number,
): Promise<void> {
  await setQty(productId, current + delta, stock);
}

async function onQtyInput(
  productId: number,
  current: number,
  stock: number,
  event: Event,
): Promise<void> {
  const value = Number((event.target as HTMLInputElement).value);
  if (Number.isInteger(value) && value >= 1 && value <= 100 && value !== current) {
    await setQty(productId, value, stock);
  }
  // 還原輸入框（re-render 由 store 狀態驅動）。
  (event.target as HTMLInputElement).value = String(current);
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

// 帶著選中品去結帳：無選擇時按鈕已 disabled，這裡是防禦。
function goCheckout(): void {
  if (selectedItems().length === 0) {
    toast.show("Select at least one item to checkout.");
    return;
  }
  void router.push({ name: "checkout" });
}

onMounted(async () => {
  if (user.value) await refresh();
  loading.value = false;
});
</script>

<template>
  <StorefrontHeader />

  <main class="storefront-main">
    <section class="page-heading">
      <div class="th-main">
        <h1>Cart</h1>
        <p>Select items, then checkout to place the order.</p>
      </div>
      <router-link :to="{ name: 'storefront' }" class="text-button">
        <Icon name="arrow" :size="15" /> Continue shopping
      </router-link>
      <div class="th-cell"><small>Sheet</small><b>CART-01</b></div>
    </section>

    <p v-if="loading" class="empty-state">Loading cart...</p>

    <!-- 訪客：車屬於登入者，引導登入後回此頁 -->
    <section v-else-if="!user" class="data-panel">
      <div class="panel-header">
        <div>
          <h2>Your cart is waiting</h2>
          <p>Carts are saved to your account — sign in to pick up where you left off.</p>
        </div>
      </div>
      <div class="cart-empty-actions">
        <router-link
          class="primary-button"
          :to="{ name: 'login', query: { redirect: '/cart' } }"
        >
          Sign in to view your cart
        </router-link>
      </div>
    </section>

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
          <table class="cart-table">
            <thead>
              <tr>
                <th class="check-col">
                  <input
                    type="checkbox"
                    :checked="allSelected()"
                    aria-label="Select all items"
                    @change="toggleAll"
                  />
                </th>
                <th>Product</th>
                <th>Unit price</th>
                <th>Stock</th>
                <th>Qty</th>
                <th>Subtotal</th>
                <th><span class="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="item in items"
                :key="item.product_id"
                :class="{ dimmed: !isSelected(item.product_id), blocked: !isSelectable(item) }"
              >
                <td class="check-col">
                  <input
                    type="checkbox"
                    :checked="isSelected(item.product_id)"
                    :disabled="!isSelectable(item)"
                    :aria-label="`Select ${item.product_name}`"
                    :title="
                      isSelectable(item)
                        ? undefined
                        : item.stock <= 0
                          ? 'Out of stock'
                          : `Only ${item.stock} in stock`
                    "
                    @change="toggleSelect(item.product_id)"
                  />
                </td>
                <td class="cart-product">
                  <strong>{{ item.product_name }}</strong>
                  <p v-if="!isSelectable(item) && item.stock > 0" class="field-error">
                    Only {{ item.stock }} in stock — reduce quantity to select.
                  </p>
                  <p v-else-if="item.stock <= 0" class="field-error">
                    Out of stock — follow it in the storefront for a restock alert.
                  </p>
                </td>
                <td class="cart-price"><span class="order-total">{{ formatPrice(item.unit_price) }}</span></td>
                <td class="cart-stock">
                  <span :class="['stock-badge', item.stock > 0 ? 'in' : 'out']">
                    {{ item.stock > 0 ? `In stock · ${item.stock}` : "Out of stock" }}
                  </span>
                </td>
                <td class="cart-qty">
                  <div class="qty-stepper">
                    <button
                      type="button"
                      :aria-label="`Decrease ${item.product_name}`"
                      :disabled="busy || item.quantity <= 1"
                      @click="step(item.product_id, item.quantity, -1, item.stock)"
                    >
                      −
                    </button>
                    <input
                      type="number"
                      min="1"
                      :max="Math.min(item.stock, 100)"
                      :value="item.quantity"
                      :aria-label="`${item.product_name} quantity`"
                      @change="onQtyInput(item.product_id, item.quantity, item.stock, $event)"
                    />
                    <button
                      type="button"
                      :aria-label="`Increase ${item.product_name}`"
                      :disabled="busy || item.quantity >= 100 || item.quantity >= item.stock"
                      @click="step(item.product_id, item.quantity, 1, item.stock)"
                    >
                      +
                    </button>
                  </div>
                </td>
                <td class="cart-subtotal"><span class="order-total">{{ formatPrice(item.subtotal) }}</span></td>
                <td class="cart-remove">
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
            <h2>Selected</h2>
            <p>
              {{ selectedCount() }} item{{ selectedCount() === 1 ? "" : "s" }} selected ·
              cart total {{ formatPrice(total) }}
            </p>
          </div>
          <span class="cart-total">{{ formatPrice(selectedTotal()) }}</span>
        </div>
        <div class="cart-summary-actions">
          <button
            type="button"
            class="primary-button"
            :disabled="busy || selectedCount() === 0"
            @click="goCheckout"
          >
            <Icon name="bolt" :size="15" />
            Checkout ({{ selectedCount() }})
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
  </main>

  <StorefrontFooter />
</template>
