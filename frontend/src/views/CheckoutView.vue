<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import Icon from "@/components/Icon.vue";
import StorefrontHeader from "@/components/StorefrontHeader.vue";
import StorefrontFooter from "@/components/StorefrontFooter.vue";
import { ApiError, api } from "@/lib/api";
import { useAuth } from "@/stores/auth";
import { useCart } from "@/stores/cart";
import { useToast } from "@/stores/toast";

// 結帳/付款頁（v1.8）：/checkout —— 檢視選中明細 → Pay → 結果頁 /checkout/result。
// 付款為 demo（POST /orders/{id}/pay 模擬）：明確標示，不假造卡號表單。
// 失敗路徑：訂單已建立但付款失敗 → 結果頁帶 order id，可到訂單詳情重試 Pay now。

const router = useRouter();
const toast = useToast();
const { user } = useAuth();
const { selectedItems, selectedTotal, checkout, refresh } = useCart();

const loading = ref(true);
const paying = ref(false);

const items = computed(() => selectedItems());
const totalNumber = computed(() => selectedTotal());

function formatPrice(price: number): string {
  return `$${price.toFixed(2)}`;
}

async function pay(): Promise<void> {
  if (items.value.length === 0) return;
  paying.value = true;

  // 先快取：checkout 會重刷車況，之後 selectedTotal 就不是這筆的金額了。
  const paidTotal = totalNumber.value.toFixed(2);

  try {
    // 1) 選中品結帳成訂單（其餘留車）
    const order = await checkout(items.value.map((item) => item.product_id));

    // 2) 付款（模擬）→ 成功到結果頁
    try {
      await api.post(`/orders/${order.id}/pay`);
      await router.push({
        name: "checkout-result",
        query: { order: String(order.id), status: "paid", total: paidTotal },
      });
    } catch (err) {
      // 訂單已成立但付款失敗：結果頁提供「到訂單重試付款」出口。
      const reason = err instanceof ApiError ? err.message : "Payment failed.";
      await router.push({
        name: "checkout-result",
        query: { order: String(order.id), status: "failed", reason },
      });
    }
  } catch (err) {
    // 結帳失敗（庫存不足等）：車未變動，回車頁並提示。
    if (err instanceof ApiError && err.message.startsWith("Insufficient product stock:")) {
      const id = Number(err.message.split(":").pop());
      const item = items.value.find((entry) => entry.product_id === id);
      toast.show(
        item
          ? `Not enough stock for "${item.product_name}".`
          : "Not enough stock for an item in your selection.",
      );
    } else {
      toast.show(err instanceof ApiError ? `Checkout failed: ${err.message}` : "Checkout failed.");
    }
    await router.push({ name: "cart" });
  } finally {
    paying.value = false;
  }
}

onMounted(async () => {
  // 訪客或無選中品 → 回車頁（車頁自有引導）。
  await refresh();
  if (!user.value || items.value.length === 0) {
    await router.replace({ name: "cart" });
    return;
  }
  loading.value = false;
});
</script>

<template>
  <StorefrontHeader />

  <main class="storefront-main">
    <section class="page-heading">
      <div class="th-main">
        <h1>Checkout</h1>
        <p>Review your selection and pay to place the order.</p>
      </div>
      <router-link :to="{ name: 'cart' }" class="text-button">
        <Icon name="arrow" :size="15" /> Back to cart
      </router-link>
      <div class="th-cell"><small>Sheet</small><b>CHECKOUT-01</b></div>
    </section>

    <p v-if="loading" class="empty-state">Loading checkout...</p>

    <template v-else>
      <section class="data-panel">
        <div class="panel-header">
          <div>
            <h2>Order summary</h2>
            <p>{{ items.length }} product{{ items.length === 1 ? "" : "s" }} · {{ items.reduce((n, i) => n + i.quantity, 0) }} units</p>
          </div>
        </div>
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Product</th>
                <th>Unit price</th>
                <th>Qty</th>
                <th>Subtotal</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in items" :key="item.product_id">
                <td><strong>{{ item.product_name }}</strong></td>
                <td><span class="order-total">{{ formatPrice(Number(item.unit_price)) }}</span></td>
                <td>{{ item.quantity }}</td>
                <td><span class="order-total">{{ formatPrice(Number(item.subtotal)) }}</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="data-panel">
        <div class="panel-header">
          <div>
            <h2>Payment method</h2>
            <p>Demo payment — simulated instantly, no real charge.</p>
          </div>
        </div>
        <div class="payment-method">
          <label class="payment-option">
            <input type="radio" name="payment" checked disabled />
            <span class="payment-option-icon"><Icon name="shield" :size="16" /></span>
            <span>
              <strong>Backend Lab Pay</strong>
              <small>Simulated · reserved at pay time</small>
            </span>
          </label>
        </div>
      </section>

      <section class="data-panel cart-summary">
        <div class="panel-header">
          <div>
            <h2>Total</h2>
            <p>Stock is reserved when you pay.</p>
          </div>
          <span class="cart-total">{{ formatPrice(totalNumber) }}</span>
        </div>
        <div class="cart-summary-actions">
          <button type="button" class="primary-button pay-button" :disabled="paying" @click="pay">
            <Icon name="bolt" :size="15" />
            {{ paying ? "Paying..." : `Pay ${formatPrice(totalNumber)}` }}
          </button>
        </div>
      </section>
    </template>
  </main>

  <StorefrontFooter />
</template>
