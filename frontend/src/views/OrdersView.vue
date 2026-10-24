<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";

import Icon from "@/components/Icon.vue";
import { ApiError, api } from "@/lib/api";
import { useAuth } from "@/stores/auth";
import { useToast } from "@/stores/toast";

// 訂單型別（後端 GET /orders 回 id、user_id、status、created_at、items）。
type OrderItem = { product_id: number; quantity: number; unit_price: string | number };

type Order = {
  id: number;
  user_id: number;
  status: string;
  created_at: string;
  items: OrderItem[];
};

// 商品下拉選項（GET /products，active only）。
type ProductOption = { id: number; name: string; price: string | number; stock: number };

const PAGE_SIZE = 10;

const orders = ref<Order[]>([]);
const page = ref(1);
const sortOrder = ref<"asc" | "desc">("desc");
const search = ref("");
const loading = ref(true);
const loadError = ref("");

const toast = useToast();
const { user: me } = useAuth();

// 一般使用者只看得到自己的訂單（每列都是自己，名字取自 session）；
// admin 會看到全部訂單，另外抓 /users 對照 user_id → 姓名。
const isAdmin = computed(() => me.value?.role === "admin");

const users = ref<{ id: number; name: string }[]>([]);
const userMap = computed(() => new Map(users.value.map((u) => [u.id, u])));

function displayName(userId: number): string {
  return (
    userMap.value.get(userId)?.name ??
    (userId === me.value?.id ? me.value?.name : undefined) ??
    userCode(userId)
  );
}

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

// ── New order（F12-3）：後端要求 items（repo 為準），v1 單商品 + 數量。──
const showCreate = ref(false);
const products = ref<ProductOption[]>([]);
const selectedProductId = ref("");
const quantity = ref("1");
const creating = ref(false);

// 目前選取的商品：數量上限與庫存提示用。
const selectedProduct = computed(() =>
  products.value.find((product) => product.id === Number(selectedProductId.value)),
);

async function openCreate(): Promise<void> {
  showCreate.value = true;

  // 每次開啟都重抓，確保庫存新鮮；demo 規模一頁 100 筆足夠。
  await loadProducts();
}

async function loadProducts(): Promise<void> {
  try {
    products.value = await api.get<ProductOption[]>("/products?page_size=100");
  } catch (err) {
    // 名稱／庫存對照失敗不阻擋列表，僅退化顯示。
    if (showCreate.value) {
      toast.show(
        err instanceof ApiError
          ? `Failed to load products: ${err.message}`
          : "Failed to load products.",
      );
    }
  }
}

// 訂單明細顯示用的商品名稱對照；抓不到就退回 #id。
function productName(productId: number): string {
  return products.value.find((product) => product.id === productId)?.name ?? `#${productId}`;
}

function orderTotal(order: Order): string {
  const total = order.items.reduce(
    (sum, item) => sum + Number(item.unit_price) * item.quantity,
    0,
  );
  return formatPrice(total);
}

function formatCreated(iso: string): string {
  return new Date(iso).toLocaleDateString();
}

function formatPrice(price: string | number): string {
  return `$${Number(price).toFixed(2)}`;
}

async function createOrder(): Promise<void> {
  const productId = Number(selectedProductId.value);
  const qty = Number(quantity.value);
  const product = products.value.find((p) => p.id === productId);

  if (!product) {
    toast.show("Select a product first.");
    return;
  }

  // 後端 OrderItemCreate：quantity gt=0 le=100。
  if (!Number.isInteger(qty) || qty < 1 || qty > 100) {
    toast.show("Quantity must be between 1 and 100.");
    return;
  }

  // 庫存先在前端擋一次，不用等後端 409。
  if (qty > product.stock) {
    toast.show(`Only ${product.stock} left in stock for "${product.name}".`);
    return;
  }

  creating.value = true;
  try {
    const created = await api.post<Order>("/orders", {
      items: [{ product_id: productId, quantity: qty }],
    });

    showCreate.value = false;
    selectedProductId.value = "";
    quantity.value = "1";
    toast.show(`Order #${created.id} created.`);

    // 新訂單 id 最大，desc 排序下在第一頁。
    page.value = 1;
    await loadOrders();
  } catch (err) {
    // 後端 409 帶內部 product_id：轉成商品名稱與剩餘庫存，別把原始訊息丟給使用者。
    if (err instanceof ApiError && err.message.startsWith("Insufficient product stock:")) {
      const id = Number(err.message.split(":").pop());
      const stale = products.value.find((p) => p.id === id);
      toast.show(
        stale
          ? `Not enough stock for "${stale.name}" (only ${stale.stock} left).`
          : "Not enough stock for the selected product.",
      );
    } else {
      toast.show(err instanceof ApiError ? `Create failed: ${err.message}` : "Create failed.");
    }
  } finally {
    creating.value = false;
  }
}

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

async function loadUsers(): Promise<void> {
  try {
    users.value = await api.get<{ id: number; name: string }[]>("/users");
  } catch {
    // 對照表失敗就退回 usr_XXXX 代碼顯示。
  }
}

onMounted(() => {
  void loadOrders();
  void loadProducts();
  if (isAdmin.value) void loadUsers();
});
watch([page, sortOrder], loadOrders);
</script>

<template>
  <section class="page-heading">
    <div class="th-main">
      <h1>Orders</h1>
      <p>Browse your orders.</p>
    </div>
    <button class="primary-button" @click="openCreate">
      <Icon name="plus" :size="15" />
      New order
    </button>

      <div class="th-cell"><small>Sheet</small><b>ORDERS-01</b></div>
    </section>

  <section v-if="showCreate" class="order-create-panel" aria-label="New order">
    <select
      v-model="selectedProductId"
      class="filter-select order-create-select"
      aria-label="Product"
    >
      <option value="" disabled>Select a product…</option>
      <option v-for="product in products" :key="product.id" :value="String(product.id)">
        {{ product.name }} — {{ formatPrice(product.price) }} (stock: {{ product.stock }})
      </option>
    </select>
    <input
      v-model="quantity"
      class="row-edit-field order-create-qty"
      type="number"
      min="1"
      :max="selectedProduct ? Math.min(selectedProduct.stock, 100) : 100"
      aria-label="Quantity"
    />
    <button type="button" class="primary-button" :disabled="creating" @click="createOrder">
      {{ creating ? "Creating..." : "Create order" }}
    </button>
    <button type="button" class="sort-button" @click="showCreate = false">Cancel</button>
    <p v-if="products.length === 0" class="order-create-hint">
      No active products — ask an admin to add some in the storefront.
    </p>
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
            <th>Items</th>
            <th>Total</th>
            <th>Status</th>
            <th>Created</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="order in filteredOrders" :key="order.id">
            <td>
              <router-link
                :to="{ name: 'order-detail', params: { id: order.id } }"
                class="order-link"
              >
                #{{ order.id }}
              </router-link>
            </td>
            <td>
              <!-- user info 詳情頁僅 admin 可用；一般使用者的訂單全是自己，顯示名字即可。 -->
              <router-link
                v-if="isAdmin"
                :to="{ name: 'admin-user-detail', params: { id: order.user_id } }"
                class="order-link user-link"
                :title="userCode(order.user_id)"
              >
                {{ displayName(order.user_id) }}
              </router-link>
              <span v-else class="order-user" :title="userCode(order.user_id)">
                {{ displayName(order.user_id) }}
              </span>
            </td>
            <td>
              <span v-for="item in order.items" :key="item.product_id" class="order-item">
                {{ productName(item.product_id) }} × {{ item.quantity }}
              </span>
            </td>
            <td>
              <span class="order-total">{{ orderTotal(order) }}</span>
            </td>
            <td>
              <span :class="['status-badge', order.status]">{{ order.status }}</span>
            </td>
            <td>
              <span class="order-date">{{ formatCreated(order.created_at) }}</span>
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
