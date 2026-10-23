<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import Icon from "@/components/Icon.vue";
import { ApiError, api } from "@/lib/api";
import { useAuth } from "@/stores/auth";
import { useToast } from "@/stores/toast";

// 公開店面（v1.4）：訪客可瀏覽 GET /products；未登入按關注 → /login?redirect=（F12-7）。
// PR-3：admin 管理控件併入本頁（F12-1）— 新增/編輯/刪除/archive + 下架清單 restore。
// Follow 星星為 session 內樂觀 UI：後端尚無「查詢我是否已關注」端點（記帳），重整不保留。

type Product = {
  id: number;
  name: string;
  description: string | null;
  image_url: string | null;
  price: string | number; // 後端 Decimal 序列化相容字串/數字
  stock: number;
};

type ProductForm = {
  name: string;
  description: string;
  image_url: string;
  price: string;
  stock: string;
};

const PAGE_SIZE = 12;

const route = useRoute();
const router = useRouter();
const { user, logout } = useAuth();
const { message: toastMessage, show: showToast, dismiss: dismissToast } = useToast();

const isAdmin = computed(() => user.value?.role === "admin");

const products = ref<Product[]>([]);
const loading = ref(true);
const loadError = ref("");
const page = ref(1);
const query = ref("");
const appliedQuery = ref("");

// 後端商品列表無 total 欄位：回滿一頁視為還有下一頁。
const hasMore = computed(() => products.value.length === PAGE_SIZE);

// 圖片載入失敗的 product id：改用預設 icon fallback。
const brokenImages = ref<Record<number, boolean>>({});

function markImageBroken(product: Product): void {
  brokenImages.value[product.id] = true;
}

// Follow 星星 toggle：點亮 = 已關注。後端 POST/DELETE follow 皆冪等。
const followedIds = ref<Record<number, boolean>>({});

async function toggleFollow(product: Product): Promise<void> {
  if (!user.value) {
    // 未登入 → 登入頁帶 redirect，登入後回店面（F12-7）。
    await router.push({ name: "login", query: { redirect: route.fullPath } });
    return;
  }

  const wasFollowed = !!followedIds.value[product.id];

  try {
    if (wasFollowed) {
      await api.delete(`/products/${product.id}/follow`);
      followedIds.value[product.id] = false;
      showToast(`Unfollowed "${product.name}".`);
    } else {
      await api.post(`/products/${product.id}/follow`);
      followedIds.value[product.id] = true;
      showToast(`Following "${product.name}" — we'll notify you when it's back in stock.`);
    }
  } catch {
    showToast("Follow failed. Please try again.");
  }
}

// ── Admin 管理狀態（F12-1）──

const showCreate = ref(false);
const editingId = ref<number | null>(null);
const busy = ref(false);

const showArchived = ref(false);
const archived = ref<Product[]>([]);
const archivedLoading = ref(false);

const createForm = ref(emptyForm());
const editForm = ref(emptyForm());

function emptyForm(): ProductForm {
  return { name: "", description: "", image_url: "", price: "", stock: "0" };
}

function formFromProduct(product: Product): ProductForm {
  return {
    name: product.name,
    description: product.description ?? "",
    image_url: product.image_url ?? "",
    price: String(product.price),
    stock: String(product.stock),
  };
}

function validateForm(form: ProductForm): boolean {
  if (!form.name.trim()) {
    showToast("Product name is required.");
    return false;
  }
  if (Number.isNaN(Number(form.price)) || Number(form.price) < 0) {
    showToast("Price must be a non-negative number.");
    return false;
  }
  if (!Number.isInteger(Number(form.stock)) || Number(form.stock) < 0) {
    showToast("Stock must be a non-negative integer.");
    return false;
  }
  return true;
}

function formPayload(form: ProductForm) {
  return {
    name: form.name.trim(),
    description: form.description.trim(),
    image_url: form.image_url.trim(),
    price: Number(form.price),
    stock: Number(form.stock),
  };
}

async function fetchProducts(): Promise<void> {
  loading.value = true;
  loadError.value = "";

  try {
    const params = new URLSearchParams({
      page: String(page.value),
      page_size: String(PAGE_SIZE),
    });

    if (appliedQuery.value) params.set("q", appliedQuery.value);

    products.value = await api.get<Product[]>(`/products?${params.toString()}`);
  } catch {
    loadError.value = "Failed to load products.";
  } finally {
    loading.value = false;
  }
}

function submitSearch(): void {
  page.value = 1;
  appliedQuery.value = query.value.trim();
  fetchProducts();
}

async function goTo(next: number): Promise<void> {
  page.value = next;
  await fetchProducts();
}

function formatPrice(price: string | number): string {
  return `$${Number(price).toFixed(2)}`;
}

async function handleLogout(): Promise<void> {
  // 登出後留在店面，header 自動切回訪客狀態。
  await logout();
}

// ── Admin CRUD（F12-1）──

async function createProduct(): Promise<void> {
  if (!validateForm(createForm.value)) return;
  busy.value = true;

  try {
    const created = await api.post<Product>("/products", formPayload(createForm.value));
    showCreate.value = false;
    createForm.value = emptyForm();
    showToast(`Product "${created.name}" created.`);
    await fetchProducts();
  } catch (err) {
    showToast(err instanceof ApiError ? `Create failed: ${err.message}` : "Create failed.");
  } finally {
    busy.value = false;
  }
}

function startEdit(product: Product): void {
  editingId.value = product.id;
  editForm.value = formFromProduct(product);
}

function cancelEdit(): void {
  editingId.value = null;
}

async function saveEdit(product: Product): Promise<void> {
  if (!validateForm(editForm.value)) return;
  busy.value = true;

  try {
    await api.patch(`/products/${product.id}`, formPayload(editForm.value));
    editingId.value = null;
    showToast(`Product "${product.name}" updated.`);
    await fetchProducts();
  } catch (err) {
    showToast(err instanceof ApiError ? `Update failed: ${err.message}` : "Update failed.");
  } finally {
    busy.value = false;
  }
}

async function deleteProduct(product: Product): Promise<void> {
  if (
    !window.confirm(
      `Delete "${product.name}"? Products referenced by existing orders cannot be deleted.`,
    )
  ) {
    return;
  }

  busy.value = true;
  try {
    await api.delete(`/products/${product.id}`);
    showToast(`Product "${product.name}" deleted.`);
    await fetchProducts();
    if (showArchived.value) await loadArchived();
  } catch (err) {
    // 被訂單引用的商品後端回 409，toast 顯示原因（F12-4：RESTRICT）。
    showToast(err instanceof ApiError ? `Delete failed: ${err.message}` : "Delete failed.");
  } finally {
    busy.value = false;
  }
}

async function archiveProduct(product: Product): Promise<void> {
  busy.value = true;
  try {
    await api.patch(`/products/${product.id}/archive`, {});
    showToast(`Product "${product.name}" archived.`);
    await fetchProducts();
  } catch (err) {
    showToast(err instanceof ApiError ? `Archive failed: ${err.message}` : "Archive failed.");
  } finally {
    busy.value = false;
  }
}

async function loadArchived(): Promise<void> {
  archivedLoading.value = true;
  try {
    archived.value = await api.get<Product[]>("/products/archived");
  } catch (err) {
    showToast(
      err instanceof ApiError
        ? `Failed to load archived products: ${err.message}`
        : "Failed to load archived products.",
    );
  } finally {
    archivedLoading.value = false;
  }
}

async function toggleArchived(): Promise<void> {
  showArchived.value = !showArchived.value;
  if (showArchived.value) await loadArchived();
}

async function restoreProduct(product: Product): Promise<void> {
  busy.value = true;
  try {
    await api.patch(`/products/${product.id}/restore`, {});
    showToast(`Product "${product.name}" restored.`);
    await loadArchived();
    await fetchProducts();
  } catch (err) {
    showToast(err instanceof ApiError ? `Restore failed: ${err.message}` : "Restore failed.");
  } finally {
    busy.value = false;
  }
}

onMounted(fetchProducts);
</script>

<template>
  <header class="storefront-header">
    <div class="brand">
      <span class="brand-mark"><Icon name="bolt" :size="16" /></span>
      <span>Backend Lab</span>
    </div>
    <div class="storefront-actions">
      <template v-if="user">
        <router-link class="ghost-button" :to="{ name: 'dashboard' }">
          <Icon name="grid" :size="14" /> Workspace
        </router-link>
        <button type="button" class="ghost-button" @click="handleLogout">
          <Icon name="logout" :size="14" /> Sign out
        </button>
      </template>
      <router-link v-else class="primary-button" :to="{ name: 'login' }">
        Sign in
      </router-link>
    </div>
  </header>

  <main class="storefront-main">
    <section class="page-heading">
      <div>
        <p class="eyebrow">Catalog</p>
        <h1>Storefront</h1>
        <p>Browse the catalog. Sign in to follow restock alerts or place orders.</p>
      </div>
      <div v-if="isAdmin" class="storefront-admin-actions">
        <button type="button" class="ghost-button" @click="toggleArchived">
          {{ showArchived ? "Hide archived" : "Archived" }}
        </button>
        <button type="button" class="primary-button" @click="showCreate = !showCreate">
          <Icon name="plus" :size="15" /> New product
        </button>
      </div>
    </section>

    <section v-if="isAdmin && showCreate" class="product-create-panel" aria-label="New product">
      <h2>New product</h2>
      <div class="product-create-fields">
        <input
          v-model="createForm.name"
          class="row-edit-field"
          type="text"
          placeholder="Name"
          aria-label="Product name"
        />
        <input
          v-model="createForm.description"
          class="row-edit-field"
          type="text"
          placeholder="Description"
          aria-label="Product description"
        />
        <input
          v-model="createForm.image_url"
          class="row-edit-field"
          type="text"
          placeholder="Image URL"
          aria-label="Product image URL"
        />
        <input
          v-model="createForm.price"
          class="row-edit-field"
          type="number"
          step="0.01"
          min="0"
          placeholder="Price"
          aria-label="Product price"
        />
        <input
          v-model="createForm.stock"
          class="row-edit-field"
          type="number"
          min="0"
          placeholder="Stock"
          aria-label="Product stock"
        />
      </div>
      <div class="order-actions">
        <button type="button" class="primary-button" :disabled="busy" @click="createProduct">
          Create
        </button>
        <button type="button" class="ghost-button" @click="showCreate = false">Cancel</button>
      </div>
    </section>

    <section class="storefront-tools">
      <div class="search-field">
        <Icon name="search" :size="15" />
        <input
          v-model="query"
          type="search"
          placeholder="Search products…"
          aria-label="Search products"
          @keydown.enter="submitSearch"
        />
      </div>
    </section>

    <section v-if="loading" class="product-grid" aria-hidden="true">
      <div v-for="n in PAGE_SIZE" :key="n" class="product-card">
        <div class="product-media"><div class="skeleton-block skeleton-media" /></div>
        <div class="product-body">
          <div class="skeleton-block skeleton-line" />
          <div class="skeleton-block skeleton-line short" />
        </div>
        <div class="product-foot">
          <div class="skeleton-block skeleton-line" style="width: 64px" />
        </div>
      </div>
    </section>
    <p v-else-if="loadError" class="empty-state">{{ loadError }}</p>
    <p v-else-if="products.length === 0" class="empty-state">No products found.</p>

    <section v-else class="product-grid" aria-label="Product catalog">
      <article v-for="product in products" :key="product.id" class="product-card">
        <!-- Admin 行內編輯模式 -->
        <div v-if="isAdmin && editingId === product.id" class="product-edit">
          <input
            v-model="editForm.name"
            class="row-edit-field"
            type="text"
            placeholder="Name"
            aria-label="Product name"
          />
          <input
            v-model="editForm.description"
            class="row-edit-field"
            type="text"
            placeholder="Description"
            aria-label="Product description"
          />
          <input
            v-model="editForm.image_url"
            class="row-edit-field"
            type="text"
            placeholder="Image URL"
            aria-label="Product image URL"
          />
          <div class="product-edit-pair">
            <input
              v-model="editForm.price"
              class="row-edit-field"
              type="number"
              step="0.01"
              min="0"
              placeholder="Price"
              aria-label="Product price"
            />
            <input
              v-model="editForm.stock"
              class="row-edit-field"
              type="number"
              min="0"
              placeholder="Stock"
              aria-label="Product stock"
            />
          </div>
          <div class="order-actions">
            <button
              type="button"
              class="primary-button"
              :disabled="busy"
              @click="saveEdit(product)"
            >
              Save
            </button>
            <button type="button" class="ghost-button" @click="cancelEdit">Cancel</button>
          </div>
        </div>

        <template v-else>
          <div class="product-media">
            <img
              v-if="product.image_url && !brokenImages[product.id]"
              :src="product.image_url"
              :alt="product.name"
              loading="lazy"
              @error="markImageBroken(product)"
            />
            <span v-else class="product-media-fallback"><Icon name="box" :size="26" /></span>
            <button
              v-if="user"
              type="button"
              :class="['follow-star', { active: followedIds[product.id] }]"
              :aria-label="
                followedIds[product.id] ? `Unfollow ${product.name}` : `Follow ${product.name}`
              "
              :aria-pressed="!!followedIds[product.id]"
              @click="toggleFollow(product)"
            >
              <Icon name="star" :size="15" />
            </button>
            <button
              v-else
              type="button"
              class="follow-star"
              :aria-label="`Sign in to follow ${product.name}`"
              @click="toggleFollow(product)"
            >
              <Icon name="star" :size="15" />
            </button>
          </div>
          <div class="product-foot">
            <span class="product-name" :title="product.name">{{ product.name }}</span>
            <div class="product-meta">
              <span v-if="product.description" class="product-desc" :title="product.description">
                {{ product.description }}
              </span>
              <span class="product-price-row">
                <span :class="['stock-badge', product.stock > 0 ? 'in' : 'out']">
                  {{ product.stock > 0 ? `In stock · ${product.stock}` : "Out of stock" }}
                </span>
                <span class="product-price">{{ formatPrice(product.price) }}</span>
              </span>
            </div>
          </div>
          <div v-if="isAdmin" class="product-admin-row">
            <button type="button" class="sort-button" @click="startEdit(product)">Edit</button>
            <button type="button" class="sort-button" @click="archiveProduct(product)">
              Archive
            </button>
            <button
              type="button"
              class="row-action row-delete"
              :aria-label="`Delete ${product.name}`"
              @click="deleteProduct(product)"
            >
              <Icon name="close" :size="14" />
            </button>
          </div>
        </template>
      </article>
    </section>

    <nav
      v-if="!loading && (products.length > 0 || page > 1)"
      class="storefront-pagination"
      aria-label="Catalog pagination"
    >
      <button type="button" :disabled="page <= 1" @click="goTo(page - 1)">Previous</button>
      <span>Page {{ page }}</span>
      <button type="button" :disabled="!hasMore" @click="goTo(page + 1)">Next</button>
    </nav>

    <section v-if="isAdmin && showArchived" class="data-panel archived-panel" aria-label="Archived products">
      <div class="panel-header">
        <div>
          <h2>Archived products</h2>
          <p>Restore to put products back on the shelf.</p>
        </div>
      </div>
      <p v-if="archivedLoading" class="empty-state">Loading archived products…</p>
      <p v-else-if="archived.length === 0" class="empty-state">No archived products.</p>
      <table v-else>
        <thead>
          <tr>
            <th>Product</th>
            <th>Price</th>
            <th>Stock</th>
            <th><span class="sr-only">Actions</span></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="product in archived" :key="product.id">
            <td><strong>{{ product.name }}</strong></td>
            <td>{{ formatPrice(product.price) }}</td>
            <td>{{ product.stock }}</td>
            <td>
              <button
                type="button"
                class="sort-button"
                :disabled="busy"
                @click="restoreProduct(product)"
              >
                Restore
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </section>
  </main>

  <Transition name="toast">
    <div v-if="toastMessage" class="toast" role="status">
      <span><Icon name="shield" :size="17" /></span>{{ toastMessage }}
      <button type="button" aria-label="Dismiss notification" @click="dismissToast">
        <Icon name="close" :size="15" />
      </button>
    </div>
  </Transition>
</template>
