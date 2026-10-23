<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";

import Icon from "@/components/Icon.vue";
import { ApiError, api } from "@/lib/api";

// 訂單型別（後端回傳只有 id 與 user_id）。
type Order = { id: number; user_id: number };

const PAGE_SIZE = 10;

const orders = ref<Order[]>([]);
const page = ref(1);
const sortOrder = ref<"asc" | "desc">("desc");
const search = ref("");
const loading = ref(true);
const loadError = ref("");

// 當前頁的客戶端搜尋（比對 id / user_id 字串）。
const filteredOrders = computed(() => {
  const q = search.value.trim();
  if (!q) return orders.value;
  return orders.value.filter(
    (o) => String(o.id).includes(q) || String(o.user_id).includes(q),
  );
});

// 回傳筆數少於 page_size 代表沒有下一頁（後端不回傳總數）。
const hasNext = computed(() => orders.value.length >= PAGE_SIZE);

async function loadOrders(): Promise<void> {
  loading.value = true;
  loadError.value = "";
  try {
    orders.value = await api.get<Order[]>(
      `/orders?page=${page.value}&page_size=${PAGE_SIZE}&sort_by=id&order=${sortOrder.value}`,
    );
  } catch (err) {
    loadError.value =
      err instanceof ApiError
        ? `Failed to load orders: ${err.message}`
        : "Failed to load orders.";
  } finally {
    loading.value = false;
  }
}

// 切換排序後回到第一頁（watch 會自動重載）。
function toggleSort(): void {
  sortOrder.value = sortOrder.value === "desc" ? "asc" : "desc";
  page.value = 1;
}

function prevPage(): void {
  if (page.value > 1) page.value -= 1;
}

function nextPage(): void {
  if (hasNext.value) page.value += 1;
}

// user_id 顯示成 usr_0024 風格的代碼。
function userCode(userId: number): string {
  return `usr_${String(userId).padStart(4, "0")}`;
}

onMounted(loadOrders);
watch([page, sortOrder], loadOrders);
</script>

<template>
  <section class="page-heading">
    <div>
      <p class="eyebrow">System workspace</p>
      <h1>Orders</h1>
      <p>Browse your orders.</p>
    </div>
    <!-- 後端自 multi-product 起要求 items（repo 為準）；商品選擇器屬 PR-3，先停用。 -->
    <button class="primary-button" disabled title="Product picker lands in the next release">
      <Icon name="plus" :size="15" />
      New order
    </button>
  </section>

  <section class="data-panel">
    <div class="panel-header">
      <div>
        <h2>All orders</h2>
        <p>Server-side pagination, 10 per page.</p>
      </div>
    </div>

    <div class="table-tools">
      <label class="search-field">
        <Icon name="search" :size="15" />
        <input v-model="search" type="search" placeholder="Filter by id or user..." />
      </label>
      <button class="sort-button" @click="toggleSort">
        id: {{ sortOrder === "desc" ? "newest" : "oldest" }}
        <Icon name="chevron" :size="14" />
      </button>
    </div>

    <div class="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Order ID</th>
            <th>User</th>
            <th><span class="sr-only">Open</span></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="order in filteredOrders" :key="order.id">
            <td>
              <span class="order-id">#{{ order.id }}</span>
            </td>
            <td>
              <code>{{ userCode(order.user_id) }}</code>
            </td>
            <td>
              <span class="row-action" aria-hidden="true">
                <Icon name="arrow" :size="16" />
              </span>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="loading" class="empty-state">Loading orders...</p>
      <p v-else-if="loadError" class="empty-state">{{ loadError }}</p>
      <p v-else-if="filteredOrders.length === 0" class="empty-state">No orders found.</p>
    </div>

    <div class="pagination">
      <p>
        Page <strong>{{ page }}</strong>
      </p>
      <div>
        <button :disabled="page <= 1" @click="prevPage">Previous</button>
        <button :disabled="!hasNext" @click="nextPage">Next</button>
      </div>
    </div>
  </section>
</template>
