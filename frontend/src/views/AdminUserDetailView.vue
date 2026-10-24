<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";

import Icon from "@/components/Icon.vue";
import { ApiError, api } from "@/lib/api";

// 使用者詳情（admin）：GET /admin/users/{id} 回基本資料 + 該使用者的全部訂單。

type OrderItem = { product_id: number; quantity: number; unit_price: string | number };

type Order = {
  id: number;
  user_id: number;
  status: string;
  created_at: string;
  items: OrderItem[];
  paid_at: string | null;
};

type UserRow = {
  id: number;
  name: string;
  email: string;
  role: string;
};

type UserDetail = { user: UserRow; orders: Order[] };

type ProductOption = { id: number; name: string };

const route = useRoute();

const detail = ref<UserDetail | null>(null);
const products = ref<ProductOption[]>([]);
const loading = ref(true);
const loadError = ref("");
const notFound = ref(false);

const initials = computed(() =>
  (detail.value?.user.name ?? "?")
    .split(" ")
    .map((part) => part[0])
    .join("")
    .toUpperCase(),
);

function productName(productId: number): string {
  return products.value.find((p) => p.id === productId)?.name ?? `#${productId}`;
}

function orderTotal(order: Order): string {
  const total = order.items.reduce(
    (sum, item) => sum + Number(item.unit_price) * item.quantity,
    0,
  );
  return `$${total.toFixed(2)}`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString();
}

onMounted(async () => {
  const userId = Number(route.params.id);

  try {
    detail.value = await api.get<UserDetail>(`/admin/users/${userId}`);
  } catch (err) {
    notFound.value = err instanceof ApiError && err.status === 404;
    loadError.value = notFound.value ? "" : "Failed to load user.";
    loading.value = false;
    return;
  }

  // 商品名稱對照失敗不阻擋頁面。
  api
    .get<ProductOption[]>("/products?page_size=100")
    .then((rows) => (products.value = rows))
    .catch(() => {});

  loading.value = false;
});
</script>

<template>
  <section class="page-heading">
    <div class="th-main">
      <h1>{{ detail?.user.name ?? "User" }}</h1>
      <p>Profile and order history.</p>
    </div>
    <router-link :to="{ name: 'admin-users' }" class="text-button">
      <Icon name="arrow" :size="15" /> Back to users
    </router-link>

      <div class="th-cell"><small>Sheet</small><b>USR-{{ route.params.id }}</b></div>
    </section>

  <p v-if="loading" class="empty-state">Loading user...</p>
  <p v-else-if="notFound" class="empty-state">User not found.</p>
  <p v-else-if="loadError" class="empty-state">{{ loadError }}</p>

  <template v-else-if="detail">
    <section class="data-panel user-detail-card" aria-label="Profile">
      <div class="user-cell">
        <span class="mini-avatar">{{ initials }}</span>
        <span>
          <strong>{{ detail.user.name }}</strong>
          <small>{{ detail.user.email }}</small>
        </span>
      </div>
      <div class="user-detail-meta">
        <span class="role-badge" :class="detail.user.role">{{ detail.user.role }}</span>
        <code>usr_{{ String(detail.user.id).padStart(4, "0") }}</code>
      </div>
    </section>

    <section class="data-panel">
      <div class="panel-header">
        <div>
          <h2>Orders</h2>
          <p>{{ detail.orders.length }} order{{ detail.orders.length === 1 ? "" : "s" }} from this user.</p>
        </div>
      </div>
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Order ID</th>
              <th>Items</th>
              <th>Total</th>
              <th>Status</th>
              <th>Created</th>
              <th><span class="sr-only">Open</span></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="order in detail.orders" :key="order.id">
              <td>
                <router-link
                  :to="{ name: 'order-detail', params: { id: order.id } }"
                  class="order-link"
                >
                  #{{ order.id }}
                </router-link>
              </td>
              <td>
                <span v-for="item in order.items" :key="item.product_id" class="order-item">
                  {{ productName(item.product_id) }} × {{ item.quantity }}
                </span>
              </td>
              <td><span class="order-total">{{ orderTotal(order) }}</span></td>
              <td><span :class="['status-badge', order.status]">{{ order.status }}</span></td>
              <td><span class="order-date">{{ formatDate(order.created_at) }}</span></td>
              <td>
                <router-link
                  :to="{ name: 'order-detail', params: { id: order.id } }"
                  class="row-action"
                  :aria-label="`Open order ${order.id}`"
                >
                  <Icon name="arrow" :size="16" />
                </router-link>
              </td>
            </tr>
          </tbody>
        </table>
        <p v-if="detail.orders.length === 0" class="empty-state">No orders from this user.</p>
      </div>
    </section>
  </template>
</template>
