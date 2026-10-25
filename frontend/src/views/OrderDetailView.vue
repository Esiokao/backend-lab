<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";

import Icon from "@/components/Icon.vue";
import PayOrderModal, { type PayLine } from "@/components/PayOrderModal.vue";
import { ApiError, api } from "@/lib/api";
import { useAuth } from "@/stores/auth";
import { useToast } from "@/stores/toast";

// 訂單詳情（F2：訂單可被檢視）。GET /orders/{id} 允許擁有者或 admin；
// 頁面含下單者的 user info 區塊（admin 可跨使用者對照並連到使用者詳情）。

type OrderItem = { product_id: number; quantity: number; unit_price: string | number };

type Order = {
  id: number;
  user_id: number;
  status: string;
  created_at: string;
  items: OrderItem[];
  paid_at: string | null;
};

type UserRow = { id: number; name: string; email: string; role: string };

const route = useRoute();
const { user: me } = useAuth();
const toast = useToast();

const isAdmin = computed(() => me.value?.role === "admin");

const order = ref<Order | null>(null);
const loading = ref(true);
const loadError = ref("");
const notFound = ref(false);

const users = ref<UserRow[]>([]);
const userMap = computed(() => new Map(users.value.map((u) => [u.id, u])));

// 下單者資訊：admin 用 /users 對照；一般使用者就是自己（session）。
const owner = computed(() => {
  if (order.value === null) return null;
  const mapped = userMap.value.get(order.value.user_id);
  if (mapped) return mapped;
  if (order.value.user_id === me.value?.id) {
    return {
      id: me.value.id,
      name: me.value.name,
      email: me.value.email,
      role: me.value.role,
    };
  }
  return null;
});

const ownerName = computed(() => owner.value?.name ?? `usr_${String(order.value?.user_id ?? "").padStart(4, "0")}`);
const ownerEmail = computed(() => owner.value?.email ?? "");
const ownerRole = computed(() => owner.value?.role ?? "user");

const ownerInitials = computed(() =>
  ownerName.value
    .split(" ")
    .map((part) => part[0])
    .join("")
    .toUpperCase(),
);

function productName(productId: number): string {
  // 明細只有 product_id；名稱對照失敗就退回 #id。
  return productNames.value.get(productId) ?? `#${productId}`;
}

const productNames = computed(() => new Map(products.value.map((p) => [p.id, p.name])));

type ProductOption = { id: number; name: string };
const products = ref<ProductOption[]>([]);

function lineTotal(item: OrderItem): string {
  return `$${(Number(item.unit_price) * item.quantity).toFixed(2)}`;
}

function orderTotal(): string {
  if (!order.value) return "$0.00";
  const total = order.value.items.reduce(
    (sum, item) => sum + Number(item.unit_price) * item.quantity,
    0,
  );
  return `$${total.toFixed(2)}`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString();
}

// 取消（v1.11）：自己的 created/pending 訂單 → POST /orders/{id}/cancel → cancelled。
const cancelling = ref(false);
const cancellable = computed(
  () =>
    order.value !== null &&
    (order.value.status === "created" || order.value.status === "pending") &&
    isOwnOrder.value,
);

async function cancelOrder(): Promise<void> {
  if (!order.value) return;
  if (!window.confirm(`Cancel order #${order.value.id}? This cannot be undone.`)) return;

  cancelling.value = true;
  try {
    await api.post(`/orders/${order.value.id}/cancel`);
    toast.show(`Order #${order.value.id} cancelled.`);
    order.value = await api.get<Order>(`/orders/${order.value.id}`);
  } catch (err) {
    toast.show(err instanceof ApiError ? `Cancel failed: ${err.message}` : "Cancel failed.");
  } finally {
    cancelling.value = false;
  }
}

// 付款（v1.20）：自己的 created 訂單 → 付款 Modal（與 checkout 同語彙）→ POST /orders/{id}/pay
// → pending（扣款模擬 + 通知）。Modal 由 title block 的 Pay now 開啟，
// 訂單列表的 Pay 捷徑則帶 ?pay=1 進來自動彈出。
const isOwnOrder = computed(() => order.value?.user_id === me.value?.id);
const payModalOpen = ref(false);
const payLines = computed<PayLine[]>(() =>
  (order.value?.items ?? []).map((item) => ({
    name: productName(item.product_id),
    quantity: item.quantity,
    amount: Number(item.unit_price) * item.quantity,
  })),
);

function openPayModal(): void {
  payModalOpen.value = true;
}

function closePayModal(): void {
  payModalOpen.value = false;
}

async function onPaid(): Promise<void> {
  payModalOpen.value = false;
  if (order.value) {
    order.value = await api.get<Order>(`/orders/${order.value.id}`);
  }
}

// 載入訂單：onMounted 與路由參數變化共用（GUI 測試抓到的 bug：
// 通知跳轉 65→66 時元件被重用，只重跑標題不重抓資料 → 標題是 66、內容是 65）。
async function loadOrder(orderId: number): Promise<void> {
  loading.value = true;
  notFound.value = false;
  loadError.value = "";

  try {
    order.value = await api.get<Order>(`/orders/${orderId}`);
  } catch (err) {
    notFound.value = err instanceof ApiError && err.status === 404;
    loadError.value = notFound.value ? "" : "Failed to load order.";
    loading.value = false;
    return;
  }

  // 訂單列表的 Pay 捷徑：?pay=1 → 載入成功後自動彈出付款 Modal（僅限本人 created 訂單）。
  if (
    route.query.pay === "1" &&
    order.value.status === "created" &&
    order.value.user_id === me.value?.id
  ) {
    payModalOpen.value = true;
  }

  // admin 補齊擁有者與商品名稱對照；失敗不阻擋頁面。
  if (isAdmin.value) {
    api
      .get<UserRow[]>("/users")
      .then((rows) => (users.value = rows))
      .catch(() => {});
  }
  api
    .get<ProductOption[]>("/products?page_size=100")
    .then((rows) => (products.value = rows))
    .catch(() => {});

  loading.value = false;
}

onMounted(() => loadOrder(Number(route.params.id)));

watch(
  () => route.params.id,
  (next, prev) => {
    if (next === prev || next === undefined) return;
    payModalOpen.value = false;
    void loadOrder(Number(next));
  },
);
</script>

<template>
  <section class="page-heading">
    <div class="th-main">
      <h1>Order #{{ route.params.id }}</h1>
      <p>Order details and line items.</p>
    </div>
    <router-link :to="{ name: 'orders' }" class="text-button">
      <Icon name="arrow" :size="15" /> Back to orders
    </router-link>

      <div class="th-cell"><small>Sheet</small><b>ORD-{{ route.params.id }}</b></div>
    </section>

  <p v-if="loading" class="empty-state">Loading order...</p>
  <p v-else-if="notFound" class="empty-state">Order not found — it may not exist, or you don't have access to it.</p>
  <p v-else-if="loadError" class="empty-state">{{ loadError }}</p>

  <template v-else-if="order">
    <section class="metrics detail-metrics" aria-label="Order summary">
      <article class="metric-card">
        <div class="metric-top">
          <span class="metric-icon violet"><Icon name="box" /></span>
        </div>
        <p>Status</p>
        <strong><span :class="['status-badge', order.status]">{{ order.status }}</span></strong>
        <small>Created {{ formatDate(order.created_at) }}</small>
      </article>
      <article class="metric-card">
        <div class="metric-top">
          <span class="metric-icon cyan"><Icon name="grid" /></span>
        </div>
        <p>Items</p>
        <strong>{{ order.items.length }}</strong>
        <small>{{ order.items.reduce((n, item) => n + item.quantity, 0) }} units total</small>
      </article>
      <article class="metric-card">
        <div class="metric-top">
          <span class="metric-icon green"><Icon name="activity" /></span>
        </div>
        <p>Total</p>
        <strong>{{ orderTotal() }}</strong>
        <small>{{ order.paid_at ? `Paid ${formatDate(order.paid_at)}` : "Not paid yet" }}</small>
      </article>
    </section>

    <section class="data-panel user-detail-card" aria-label="Order owner">
      <div class="user-cell">
        <span class="mini-avatar">{{ ownerInitials }}</span>
        <span>
          <router-link
            v-if="isAdmin"
            :to="{ name: 'admin-user-detail', params: { id: order.user_id } }"
            class="order-link user-link"
          >
            <strong>{{ ownerName }}</strong>
          </router-link>
          <strong v-else>{{ ownerName }}</strong>
          <small>{{ ownerEmail || `usr_${String(order.user_id).padStart(4, "0")}` }}</small>
        </span>
      </div>
      <div class="user-detail-meta">
        <span class="role-badge" :class="ownerRole">{{ ownerRole }}</span>
        <code>usr_{{ String(order.user_id).padStart(4, "0") }}</code>
      </div>
    </section>

    <section class="data-panel">
      <div class="panel-header">
        <div>
          <h2>Line items</h2>
          <p>Unit price is snapshotted at order time.</p>
        </div>
      </div>
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Product</th>
              <th>Unit price</th>
              <th>Qty</th>
              <th>Line total</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in order.items" :key="item.product_id">
              <td><strong>{{ productName(item.product_id) }}</strong></td>
              <td><span class="order-total">${{ Number(item.unit_price).toFixed(2) }}</span></td>
              <td>{{ item.quantity }}</td>
              <td><span class="order-total">{{ lineTotal(item) }}</span></td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- 付款到期：與取消同樣放在 Line items 下方——title block 只留身份，動作跟著明細走。 -->
    <section
      v-if="order.status === 'created' && isOwnOrder"
      class="data-panel pay-strip"
      aria-label="Pay order"
    >
      <div>
        <strong>Payment due</strong>
        <p>Stock is reserved for this order. Pay to confirm it.</p>
      </div>
      <button type="button" class="primary-button" @click="openPayModal">
        <Icon name="bolt" :size="15" /> Pay now · {{ orderTotal() }}
      </button>
    </section>

    <!-- 取消訂單：danger strip。 -->
    <section v-if="cancellable" class="data-panel cancel-strip" aria-label="Cancel order">
      <div>
        <strong>Cancel this order</strong>
        <p>Unpaid orders only. Cancelling cannot be undone.</p>
      </div>
      <button type="button" class="ghost-button cancel-button" :disabled="cancelling" @click="cancelOrder">
        <Icon name="close" :size="14" /> {{ cancelling ? "Cancelling..." : "Cancel order" }}
      </button>
    </section>
  </template>

  <PayOrderModal
    v-if="order && payModalOpen"
    :order-id="order.id"
    :lines="payLines"
    @close="closePayModal"
    @paid="onPaid"
  />
</template>
