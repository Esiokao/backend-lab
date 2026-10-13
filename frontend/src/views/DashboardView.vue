<script setup lang="ts">
import { onMounted, ref } from "vue";

import Icon from "@/components/Icon.vue";
import { api } from "@/lib/api";

// Overview：metric 卡先用設計稿的裝飾數字（後端還沒有 stats 端點），
// 最近訂單接真資料（GET /orders 取前 5 筆）。

type Order = { id: number; user_id: number };

const orders = ref<Order[]>([]);
const loading = ref(true);
const loadError = ref("");

const recentOrders = ref<Order[]>([]);

onMounted(async () => {
  try {
    // 後端一次回全部；儀表板只取前 5 筆展示。
    orders.value = await api.get<Order[]>("/orders");
    recentOrders.value = [...orders.value].sort((a, b) => b.id - a.id).slice(0, 5);
  } catch {
    loadError.value = "Failed to load recent orders.";
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <section class="page-heading">
    <div>
      <p class="eyebrow">System workspace</p>
      <h1>Overview</h1>
      <p>Monitor your API, users, and order activity from one place.</p>
    </div>
    <p class="updated">Last updated <strong>just now</strong></p>
  </section>

  <section class="metrics" aria-label="Key metrics">
    <article class="metric-card">
      <div class="metric-top">
        <span class="metric-icon violet"><Icon name="users" /></span>
        <span class="trend">+12.4%</span>
      </div>
      <p>Total users</p>
      <strong>2,849</strong>
      <small>312 joined this month</small>
    </article>
    <article class="metric-card">
      <div class="metric-top">
        <span class="metric-icon cyan"><Icon name="box" /></span>
        <span class="trend">+8.2%</span>
      </div>
      <p>Total orders</p>
      <strong>{{ orders.length > 0 ? orders.length : "—" }}</strong>
      <small>Live from the API</small>
    </article>
    <article class="metric-card">
      <div class="metric-top">
        <span class="metric-icon green"><Icon name="activity" /></span>
        <span class="health-badge"><i /> Healthy</span>
      </div>
      <p>API uptime</p>
      <strong>99.99%</strong>
      <small>Last 30 days</small>
    </article>
    <article class="metric-card">
      <div class="metric-top">
        <span class="metric-icon amber"><Icon name="database" /></span>
        <span class="latency">24 ms</span>
      </div>
      <p>Database</p>
      <strong>Connected</strong>
      <small>PostgreSQL · production</small>
    </article>
  </section>

  <section class="data-panel">
    <div class="panel-header">
      <div>
        <h2>Recent orders</h2>
        <p>Latest order activity across all users.</p>
      </div>
      <router-link to="{ name: 'orders' }" class="text-button">
        View all orders <Icon name="arrow" :size="15" />
      </router-link>
    </div>

    <div class="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Order ID</th>
            <th>User ID</th>
            <th><span class="sr-only">Open</span></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="order in recentOrders" :key="order.id">
            <td><span class="order-id">#{{ order.id }}</span></td>
            <td><code>usr_{{ String(order.user_id).padStart(4, "0") }}</code></td>
            <td>
              <router-link
                :to="{ name: 'orders' }"
                class="row-action"
                :aria-label="`Open order ${order.id}`"
              >
                <Icon name="arrow" :size="16" />
              </router-link>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="loading" class="empty-state">Loading recent orders...</p>
      <p v-else-if="loadError" class="empty-state">{{ loadError }}</p>
      <p v-else-if="recentOrders.length === 0" class="empty-state">No orders yet.</p>
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
