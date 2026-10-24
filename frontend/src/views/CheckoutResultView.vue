<script setup lang="ts">
import { onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";

import Icon from "@/components/Icon.vue";
import StorefrontHeader from "@/components/StorefrontHeader.vue";

// 結帳結果頁（v1.8）：/checkout/result?order=N&status=paid|failed[&total=][&reason=]
// paid → 完成畫面（看訂單 / 繼續購物）；failed → 訂單已成立但付款失敗（到訂單重試 Pay now）。
// query 不完整（如直接開頁/重整前次狀態已消費）→ 回車頁。

const route = useRoute();
const router = useRouter();

const orderId = Number(route.query.order);
const status = route.query.status === "paid" ? "paid" : "failed";
const total = typeof route.query.total === "string" ? route.query.total : null;
const reason = typeof route.query.reason === "string" ? route.query.reason : "";

onMounted(() => {
  if (!Number.isInteger(orderId) || orderId <= 0) {
    void router.replace({ name: "cart" });
  }
});
</script>

<template>
  <StorefrontHeader />

  <main class="storefront-main">
    <section v-if="orderId > 0" :class="['result-hero', status]" role="status">
      <span :class="['result-icon', status]">
        <Icon :name="status === 'paid' ? 'check' : 'close'" :size="30" />
      </span>
      <h1>{{ status === "paid" ? "Payment complete" : "Payment failed" }}</h1>
      <p v-if="status === 'paid'">
        Order #{{ orderId }} is paid{{ total ? ` — $${Number(total).toFixed(2)}` : "" }} and on its way.
      </p>
      <p v-else>
        Order #{{ orderId }} was created, but payment didn't go through.
        <template v-if="reason">{{ reason }}</template>
        You can retry from the order page — your items are safe.
      </p>
      <div class="result-actions">
        <router-link
          class="primary-button"
          :to="{ name: 'order-detail', params: { id: orderId } }"
        >
          View order #{{ orderId }}
        </router-link>
        <router-link
          class="ghost-button"
          :to="{ name: status === 'paid' ? 'storefront' : 'cart' }"
        >
          {{ status === "paid" ? "Continue shopping" : "Back to cart" }}
        </router-link>
      </div>
    </section>
  </main>
</template>
