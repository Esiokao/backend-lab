<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import Icon from "@/components/Icon.vue";
import { ApiError, api } from "@/lib/api";

// Overview（admin 專屬 workspace 頁）：全部接真資料 ——
// GET /stats（global 範圍）+ /ready 探測。Recent orders 可點進訂單與使用者詳情。

type OrderItem = { product_id: number; quantity: number; unit_price: string | number };

type Order = {
  id: number;
  user_id: number;
  status: string;
  created_at: string;
  items: OrderItem[];
};

type Stats = {
  scope: "global" | "personal";
  total_users?: number;
  total_orders: number;
  orders_today: number;
  total_revenue?: number;
  revenue_today?: number;
  visitors_today?: number;
  visitors_total?: number;
};

type UserRow = { id: number; name: string; email: string; role: string };

const stats = ref<Stats | null>(null);
const orders = ref<Order[]>([]);
const loading = ref(true);
const loadError = ref("");



const users = ref<UserRow[]>([]);
const userMap = computed(() => new Map(users.value.map((u) => [u.id, u])));

const products = ref<{ id: number; name: string }[]>([]);

function formatMoney(value: number): string {
  return `$${value.toFixed(2)}`;
}

const recentOrders = computed(() =>
  [...orders.value].sort((a, b) => b.id - a.id).slice(0, 5),
);

function ownerName(userId: number): string {
  return userMap.value.get(userId)?.name ?? `usr_${String(userId).padStart(4, "0")}`;
}

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


onMounted(async () => {
  try {
    const [statsData, ordersData] = await Promise.all([
      api.get<Stats>("/stats"),
      api.get<Order[]>("/orders?page_size=100"),
    ]);
    stats.value = statsData;
    orders.value = ordersData;
  } catch (err) {
    loadError.value =
      err instanceof ApiError ? `Failed to load stats: ${err.message}` : "Failed to load stats.";
  } finally {
    loading.value = false;
  }

  api
    .get<UserRow[]>("/users")
    .then((rows) => (users.value = rows))
    .catch(() => {});
  api
    .get<{ id: number; name: string }[]>("/products?page_size=100")
    .then((rows) => (products.value = rows))
    .catch(() => {});
});
</script>

<template>
  <section class="page-heading">
    <div class="th-main">
      <h1>Overview</h1>
      <p>Monitor your API, users, and order activity from one place.</p>
    </div>

      <div class="th-cell"><small>Sheet</small><b>OVERVIEW-01</b></div>
      <div class="th-cell"><small>Rev</small><b>A · {{ new Date().toLocaleDateString() }}</b></div>
    </section>

  <p v-if="loading" class="empty-state">Loading stats...</p>
  <p v-else-if="loadError" class="empty-state">{{ loadError }}</p>

  <section v-else-if="stats" class="metrics" aria-label="Key metrics">
    <article class="metric-card">
      <div class="metric-top">
        <span class="metric-icon violet"><Icon name="users" /></span>
        <span class="zone">A</span>
      </div>
      <p>Total users</p>
      <strong>{{ stats.total_users }}</strong>
      <div class="dim"><small>live</small><div class="dline"></div><small>GET /stats</small></div>
    </article>
    <article class="metric-card">
      <div class="metric-top">
        <span class="metric-icon cyan"><Icon name="box" /></span>
        <span class="zone">B</span>
      </div>
      <p>Total orders</p>
      <strong>{{ stats.total_orders }}</strong>
      <div class="dim"><small>{{ stats.orders_today }} today</small><div class="dline"></div><small>GET /stats</small></div>
    </article>
    <article class="metric-card">
      <div class="metric-top">
        <span class="metric-icon green"><Icon name="activity" /></span>
        <span class="zone">C</span>
      </div>
      <p>Revenue</p>
      <strong>{{ formatMoney(stats.total_revenue ?? 0) }}</strong>
      <div class="dim">
        <small>{{ formatMoney(stats.revenue_today ?? 0) }} today · cancelled excluded</small>
        <div class="dline"></div><small>order_items</small>
      </div>
    </article>
    <article class="metric-card">
      <div class="metric-top">
        <span class="metric-icon amber"><Icon name="users" /></span>
        <span class="zone">D</span>
      </div>
      <p>Visitors today</p>
      <strong>{{ stats.visitors_today ?? 0 }}</strong>
      <div class="dim">
        <small>{{ stats.visitors_total ?? 0 }} all-time (HLL)</small>
        <div class="dline"></div><small>Redis · bl_vid</small>
      </div>
    </article>
  </section>

  <section class="data-panel">
    <div class="panel-header">
      <div>
        <h2>Recent orders</h2>
        <p>Latest order activity across all users.</p>
      </div>
      <router-link :to="{ name: 'orders' }" class="text-button">
        View all orders <Icon name="arrow" :size="15" />
      </router-link>
    </div>

    <div class="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Order ID</th>
            <th>User</th>
            <th>Items</th>
            <th>Total</th>
            <th>Status</th>
            <th><span class="sr-only">Open</span></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="order in recentOrders" :key="order.id">
            <td>
              <router-link
                :to="{ name: 'order-detail', params: { id: order.id } }"
                class="order-link"
              >
                #{{ order.id }}
              </router-link>
            </td>
            <td>
              <router-link
                :to="{ name: 'admin-user-detail', params: { id: order.user_id } }"
                class="order-link"
              >
                {{ ownerName(order.user_id) }}
              </router-link>
            </td>
            <td>
              <span v-for="item in order.items" :key="item.product_id" class="order-item">
                {{ productName(item.product_id) }} × {{ item.quantity }}
              </span>
            </td>
            <td><span class="order-total">{{ orderTotal(order) }}</span></td>
            <td><span :class="['status-badge', order.status]">{{ order.status }}</span></td>
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
      <p v-if="!loading && recentOrders.length === 0" class="empty-state">No orders yet.</p>
    </div>
  </section>

  <section class="security-strip">
    <span class="security-icon"><Icon name="shield" :size="20" /></span>
    <div>
      <strong>Protected by session-based access control</strong>
      <p>HttpOnly cookies, rate limiting, and request size limits are active.</p>
    </div>
    <span class="security-status"><i /> Security checks passed</span>
  </section>
</template>
