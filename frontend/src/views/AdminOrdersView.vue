<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";

import Icon from "@/components/Icon.vue";
import { ApiError, api } from "@/lib/api";
import { useToast } from "@/stores/toast";

// Admin 訂單管理（F8）。後端契約（以 repo 為準）：
// - GET /admin/orders → { items: [{id, user_id, status}], total, page, page_size }
//   items 不含擁有者欄位 → 擁有者 name/email 由 admin 的 GET /users 對照（F8-1）
// - PATCH /admin/orders/{id}/status?new_status=X（非法轉移 → 409，F8-4）
// - DELETE /admin/orders/{id} → 204（F8-5）

type OrderStatusValue = "created" | "pending" | "processing" | "completed" | "cancelled";

type AdminOrder = { id: number; user_id: number; status: OrderStatusValue };

type AdminOrdersResponse = {
  items: AdminOrder[];
  total: number;
  page: number;
  page_size: number;
};

type UserRow = { id: number; name: string; email: string; role: string };

const STATUSES: OrderStatusValue[] = [
  "created",
  "pending",
  "processing",
  "completed",
  "cancelled",
];

// 鏡像後端 app/core/enums.py 的 ALLOWED_TRANSITIONS：UI 只允許合法的下一狀態。
const ALLOWED_TRANSITIONS: Record<OrderStatusValue, OrderStatusValue[]> = {
  created: ["pending", "cancelled"],
  pending: ["processing", "completed", "cancelled"],
  processing: ["completed", "cancelled"],
  completed: [],
  cancelled: [],
};

const PAGE_SIZE = 10;

const orders = ref<AdminOrder[]>([]);
const total = ref(0);
const page = ref(1);
const statusFilter = ref<OrderStatusValue | "all">("all");
const userIdFilter = ref("");
const users = ref<UserRow[]>([]);
const loading = ref(true);
const loadError = ref("");

const toast = useToast();

// 擁有者對照表：user_id → { name, email }。
const userMap = computed(() => new Map(users.value.map((user) => [user.id, user])));

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)));
const hasNext = computed(() => page.value < totalPages.value);

async function loadOrders(): Promise<void> {
  loading.value = true;
  loadError.value = "";

  try {
    const params = new URLSearchParams({
      page: String(page.value),
      page_size: String(PAGE_SIZE),
    });

    if (statusFilter.value !== "all") params.set("status", statusFilter.value);

    const userId = userIdFilter.value.trim();
    if (userId) params.set("user_id", userId);

    const data = await api.get<AdminOrdersResponse>(`/admin/orders?${params.toString()}`);
    orders.value = data.items;
    total.value = data.total;

    // 刪除後總數縮水，目前頁可能超出範圍 → 收回最後一頁。
    if (page.value > totalPages.value) {
      page.value = totalPages.value;
      await loadOrders();
    }
  } catch (err) {
    loadError.value =
      err instanceof ApiError ? `Failed to load orders: ${err.message}` : "Failed to load orders.";
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  // 對照表載入失敗不阻擋列表，僅退回 usr_XXXX 顯示。
  try {
    users.value = await api.get<UserRow[]>("/users");
  } catch {
    users.value = [];
  }
  await loadOrders();
});

watch(page, loadOrders);

function applyFilters(): void {
  const raw = userIdFilter.value.trim();
  if (raw && (!/^\d+$/.test(raw) || Number(raw) < 1)) {
    toast.show("User ID filter must be a positive integer.");
    return;
  }
  page.value = 1;
  loadOrders();
}

// 狀態轉移：非法轉移由後端擋（409），toast 顯示原因後重載還原（F8-3/4）。
async function changeStatus(order: AdminOrder, next: OrderStatusValue): Promise<void> {
  try {
    await api.patch(`/admin/orders/${order.id}/status?new_status=${next}`, {});
    toast.show(`Order #${order.id} → ${next}.`);
  } catch (err) {
    toast.show(err instanceof ApiError ? `Update failed: ${err.message}` : "Update failed.");
  }
  await loadOrders();
}

async function deleteOrder(order: AdminOrder): Promise<void> {
  if (!window.confirm(`Delete order #${order.id}? This cannot be undone.`)) return;

  try {
    await api.delete(`/admin/orders/${order.id}`);
    toast.show(`Order #${order.id} deleted.`);
  } catch (err) {
    toast.show(err instanceof ApiError ? `Delete failed: ${err.message}` : "Delete failed.");
  }
  await loadOrders();
}

function userCode(userId: number): string {
  return `usr_${String(userId).padStart(4, "0")}`;
}

function ownerName(userId: number): string {
  return userMap.value.get(userId)?.name ?? userCode(userId);
}

function ownerEmail(userId: number): string {
  return userMap.value.get(userId)?.email ?? "unknown user";
}

function ownerInitials(userId: number): string {
  const name = userMap.value.get(userId)?.name ?? "";
  return name.trim().slice(0, 2).toUpperCase() || "??";
}

function onStatusChange(order: AdminOrder, event: Event): void {
  const value = (event.target as HTMLSelectElement).value as OrderStatusValue;
  if (value !== order.status) changeStatus(order, value);
}
</script>

<template>
  <section class="page-heading">
    <div class="th-main">
      <h1>Order Management</h1>
      <p>All orders across users, with status control.</p>
    </div>

      <div class="th-cell"><small>Sheet</small><b>ADMIN-ORD-01</b></div>
    </section>

  <section class="data-panel">
    <div class="panel-header">
      <div>
        <h2>All orders</h2>
        <p>Server-side pagination, 10 per page.</p>
      </div>
    </div>

    <div class="table-tools">
      <div class="table-tools-group">
        <label class="search-field">
          <Icon name="users" :size="14" />
          <input
            v-model="userIdFilter"
            type="text"
            inputmode="numeric"
            placeholder="Filter by user ID"
            aria-label="Filter by user ID"
            @keydown.enter="applyFilters"
            @change="applyFilters"
          />
        </label>
        <select
          v-model="statusFilter"
          class="filter-select"
          aria-label="Filter by status"
          @change="applyFilters"
        >
          <option value="all">All statuses</option>
          <option v-for="status in STATUSES" :key="status" :value="status">{{ status }}</option>
        </select>
      </div>
      <span class="result-count"><strong>{{ total }}</strong> orders</span>
    </div>

    <div class="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Order ID</th>
            <th>User</th>
            <th>Status</th>
            <th><span class="sr-only">Actions</span></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="order in orders" :key="order.id">
            <td>
              <span class="order-id">#{{ order.id }}</span>
            </td>
            <td>
              <div class="user-cell">
                <span class="mini-avatar">{{ ownerInitials(order.user_id) }}</span>
                <span>
                  <router-link
                    :to="{ name: 'admin-user-detail', params: { id: order.user_id } }"
                    class="order-link user-link"
                  >
                    <strong>{{ ownerName(order.user_id) }}</strong>
                  </router-link>
                  <small>{{ ownerEmail(order.user_id) }}</small>
                </span>
              </div>
            </td>
            <td>
              <span :class="['status-badge', order.status]">{{ order.status }}</span>
            </td>
            <td>
              <div class="order-actions">
                <select
                  class="filter-select"
                  :value="order.status"
                  :aria-label="`Change status for order ${order.id}`"
                  @change="onStatusChange(order, $event)"
                >
                  <option
                    v-for="status in STATUSES"
                    :key="status"
                    :value="status"
                    :disabled="
                      status === order.status ||
                      !ALLOWED_TRANSITIONS[order.status].includes(status)
                    "
                  >
                    {{ status }}
                  </option>
                </select>
                <button
                  type="button"
                  class="row-action row-delete"
                  :aria-label="`Delete order ${order.id}`"
                  @click="deleteOrder(order)"
                >
                  <Icon name="close" :size="15" />
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="loading" class="empty-state">Loading orders...</p>
      <p v-else-if="loadError" class="empty-state">{{ loadError }}</p>
      <p v-else-if="orders.length === 0" class="empty-state">No orders found.</p>
    </div>

    <div class="pagination">
      <p>
        Page <strong>{{ page }}</strong> of <strong>{{ totalPages }}</strong>
      </p>
      <div>
        <button :disabled="page <= 1" @click="page -= 1">Previous</button>
        <button :disabled="!hasNext" @click="page += 1">Next</button>
      </div>
    </div>
  </section>
</template>
