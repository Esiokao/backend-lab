<script setup lang="ts">
import { computed, onMounted, ref, watch, type Ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import Icon from "@/components/Icon.vue";
import StorefrontHeader from "@/components/StorefrontHeader.vue";
import { ApiError, api } from "@/lib/api";
import {
  CategoryPageSchema,
  ProductFormSchema,
  ProductListSchema,
  type Category,
  type Product,
} from "@/lib/schemas";
import { useAuth } from "@/stores/auth";
import { useCart } from "@/stores/cart";
import { useToast } from "@/stores/toast";

// 公開店面（v1.4）：訪客可瀏覽 GET /products；未登入按關注 → /login?redirect=（F12-7）。
// v1.6：市集型錄 —— 左側分類導覽（GET /categories 公開）+ 商品卡分類標籤；
// admin 管理控件併入本頁（F12-1）— 商品 CRUD/archive；分類 CRUD 在 /admin/categories 專頁。
// Follow 星星為 session 內樂觀 UI：後端尚無「查詢我是否已關注」端點（記帳），重整不保留。

type ProductForm = {
  name: string;
  description: string;
  image_url: string;
  price: string;
  stock: string;
  category_id: string; // select 值；空字串 = 未分類
};

const PAGE_SIZE = 12;
const NEW_IN_DAYS = 7;

const route = useRoute();
const router = useRouter();

// ?cat=<id> deep-link：header 分類導覽與側欄共用同一個過濾狀態。
function categoryFromQuery(): number | null {
  const cat = Number(route.query.cat);
  return Number.isInteger(cat) && cat > 0 ? cat : null;
}

const { user } = useAuth();
const { add: addToCart } = useCart();
const { show: showToast } = useToast();

const isAdmin = computed(() => user.value?.role === "admin");

const products = ref<Product[]>([]);
const loading = ref(true);
const loadError = ref("");
const page = ref(1);
const query = ref("");
const appliedQuery = ref("");

// ── 分類導覽（v1.6 catalog）──
const categories = ref<Category[]>([]);
const allProducts = ref<Product[]>([]);
const selectedCategory = ref<number | null>(null);

const categoryMap = computed(() => new Map(categories.value.map((c) => [c.id, c])));

function categoryName(id: number | null): string {
  return id === null ? "Uncategorized" : (categoryMap.value.get(id)?.name ?? "Uncategorized");
}

// 各分類商品數（admin 含下架；訪客所見以架上為準——計數用同一份即可，demo 規模）。
const categoryCounts = computed(() => {
  const counts = new Map<number, number>();
  for (const product of allProducts.value) {
    if (product.category_id !== null) {
      counts.set(product.category_id, (counts.get(product.category_id) ?? 0) + 1);
    }
  }
  return counts;
});

// NEW IN：7 天內建立的商品（真實資料推導，非裝飾）。
function isNew(product: Product): boolean {
  const created = new Date(product.created_at).getTime();
  return Date.now() - created < NEW_IN_DAYS * 24 * 60 * 60 * 1000;
}

async function fetchCategories(): Promise<void> {
  try {
    const data = await api.get("/categories", CategoryPageSchema);
    categories.value = data.items;
  } catch {
    // 分類導覽抓不到不阻擋商品列表。
  }
}

async function fetchAllForCounts(): Promise<void> {
  try {
    allProducts.value = await api.get("/products?page_size=100", ProductListSchema);
  } catch {
    // 計數失敗安靜退場。
  }
}

function selectCategory(id: number | null): void {
  selectedCategory.value = id;
  page.value = 1;
  void fetchProducts();
}

// 後端商品列表無 total 欄位：回滿一頁視為還有下一頁。
const hasMore = computed(() => products.value.length === PAGE_SIZE);

// 圖片載入失敗的 product id：改用預設 icon fallback。
const brokenImages = ref<Record<number, boolean>>({});

function markImageBroken(product: Product): void {
  brokenImages.value[product.id] = true;
}

// Follow 星星 toggle：點亮 = 已關注。後端 POST/DELETE follow 皆冂等。
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
      // 到貨通知只發生在 0 → >0 的補貨；還有庫存的商品別開這張空頭支票。
      showToast(
        product.stock > 0
          ? `Following "${product.name}".`
          : `Following "${product.name}" — we'll notify you when it's back in stock.`,
      );
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
  // stock 留空（送出時 Number("") = 0），與其他欄位一致顯示 placeholder。
  return { name: "", description: "", image_url: "", price: "", stock: "", category_id: "" };
}

function formFromProduct(product: Product): ProductForm {
  return {
    name: product.name,
    description: product.description ?? "",
    image_url: product.image_url ?? "",
    price: String(product.price),
    stock: String(product.stock),
    category_id: product.category_id === null ? "" : String(product.category_id),
  };
}

// zod 表單驗證：錯誤 inline 顯示在欄位下（create 與 edit 共用欄位鍵）。
const createErrors = ref<Record<string, string>>({});
const editErrors = ref<Record<string, string>>({});

function runFormValidation(
  form: ProductForm,
  errors: Ref<Record<string, string>>,
): { name: string; description: string; image_url: string; price: number; stock: number } | null {
  const parsed = ProductFormSchema.safeParse({
    name: form.name,
    description: form.description,
    image_url: form.image_url,
    price: form.price,
    stock: form.stock,
  });
  if (!parsed.success) {
    errors.value = Object.fromEntries(
      parsed.error.issues.map((issue) => [String(issue.path[0] ?? ""), issue.message]),
    );
    return null;
  }
  errors.value = {};
  return parsed.data;
}

function formPayload(validated: NonNullable<ReturnType<typeof runFormValidation>>, form: ProductForm) {
  return {
    name: validated.name,
    description: validated.description.trim(),
    image_url: validated.image_url.trim(),
    price: validated.price,
    stock: validated.stock,
    category_id: form.category_id === "" ? null : Number(form.category_id),
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
    if (selectedCategory.value !== null) {
      params.set("category_id", String(selectedCategory.value));
    }

    products.value = await api.get(`/products?${params.toString()}`, ProductListSchema);
  } catch {
    loadError.value = "Failed to load products.";
  } finally {
    loading.value = false;
  }
}

// 商品/分類變動後同步刷新：列表、分類、計數。
async function refreshCatalog(): Promise<void> {
  await Promise.all([fetchProducts(), fetchCategories(), fetchAllForCounts()]);
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

// 加入購物車（v1.7）：訪客 → 登入頁帶 redirect（同 follow 行為）。
async function handleAddToCart(product: Product): Promise<void> {
  if (!user.value) {
    await router.push({ name: "login", query: { redirect: route.fullPath } });
    return;
  }
  if (product.stock <= 0) {
    showToast(`"${product.name}" is out of stock.`);
    return;
  }
  try {
    await addToCart(product.id, 1);
    showToast(`Added "${product.name}" to cart.`);
  } catch (err) {
    showToast(err instanceof ApiError ? `Add to cart failed: ${err.message}` : "Add to cart failed.");
  }
}

// ── Admin 商品 CRUD（F12-1）──

async function createProduct(): Promise<void> {
  const validated = runFormValidation(createForm.value, createErrors);
  if (validated === null) return;
  busy.value = true;

  try {
    const created = await api.post<Product>("/products", formPayload(validated, createForm.value));
    showCreate.value = false;
    createForm.value = emptyForm();
    showToast(`Product "${created.name}" created.`);
    await refreshCatalog();
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
  const validated = runFormValidation(editForm.value, editErrors);
  if (validated === null) return;
  busy.value = true;

  try {
    await api.patch(`/products/${product.id}`, formPayload(validated, editForm.value));
    editingId.value = null;
    showToast(`Product "${product.name}" updated.`);
    await refreshCatalog();
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
    await refreshCatalog();
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
    await refreshCatalog();
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
    await refreshCatalog();
  } catch (err) {
    showToast(err instanceof ApiError ? `Restore failed: ${err.message}` : "Restore failed.");
  } finally {
    busy.value = false;
  }
}

// 所在位置反映：標題塊 h1 與分頁標題跟著分類走（在哪裡就顯示在哪裡）。
const headingTitle = computed(() =>
  selectedCategory.value === null ? "Storefront" : categoryName(selectedCategory.value),
);
const headingSub = computed(() => {
  if (selectedCategory.value !== null) {
    const name = categoryName(selectedCategory.value);
    const n = products.value.length;
    return `Browsing ${name} — ${n} product${n === 1 ? "" : "s"}.`;
  }
  return user.value
    ? "Follow products for restock alerts, or place orders from your workspace."
    : "Browse the catalog. Sign in to follow restock alerts or place orders.";
});

// 分頁標題同步（覆寫 router 的靜態 title）。
watch(
  headingTitle,
  (title) => {
    document.title = `${title} · Backend Lab`;
  },
  { immediate: true },
);
// 同頁切分類（header 連結）→ route.query 變化 → 重選分類。
watch(
  () => route.query.cat,
  () => {
    const next = categoryFromQuery();
    if (next !== selectedCategory.value) {
      selectedCategory.value = next;
      page.value = 1;
      void fetchProducts();
    }
  },
);

onMounted(() => {
  selectedCategory.value = categoryFromQuery();
  void fetchProducts();
  void fetchCategories();
  void fetchAllForCounts();
});
</script>

<template>
  <StorefrontHeader />

  <main class="storefront-main">
    <section class="page-heading">
      <div class="th-main">
        <h1>{{ headingTitle }}</h1>
        <p>{{ headingSub }}</p>
      </div>
      <div v-if="isAdmin" class="storefront-admin-actions">
        <button type="button" class="ghost-button" @click="toggleArchived">
          {{ showArchived ? "Hide archived" : "Archived" }}
        </button>
        <button type="button" class="primary-button" @click="showCreate = !showCreate">
          <Icon name="plus" :size="15" /> New product
        </button>
      </div>
      <div class="th-cell">
        <small>Sheet</small>
        <b>{{
          selectedCategory === null ? "STORE-01" : `CAT-${String(selectedCategory).padStart(2, "0")}`
        }}</b>
      </div>
    </section>

    <section v-if="isAdmin && showCreate" class="product-create-panel" aria-label="New product">
      <h2>New product</h2>
      <div class="product-create-fields">
        <div class="form-field">
          <input
            v-model="createForm.name"
            class="row-edit-field"
            type="text"
            placeholder="Name"
            aria-label="Product name"
          />
          <p v-if="createErrors.name" class="field-error">{{ createErrors.name }}</p>
        </div>
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
        <select v-model="createForm.category_id" class="filter-select" aria-label="Product category">
          <option value="">Uncategorized</option>
          <option v-for="category in categories" :key="category.id" :value="String(category.id)">
            {{ category.name }}
          </option>
        </select>
        <div class="form-field">
          <input
            v-model="createForm.price"
            class="row-edit-field"
            type="number"
            step="0.01"
            min="0"
            placeholder="Price"
            aria-label="Product price"
          />
          <p v-if="createErrors.price" class="field-error">{{ createErrors.price }}</p>
        </div>
        <div class="form-field">
          <input
            v-model="createForm.stock"
            class="row-edit-field"
            type="number"
            min="0"
            placeholder="Stock"
            aria-label="Product stock"
          />
          <p v-if="createErrors.stock" class="field-error">{{ createErrors.stock }}</p>
        </div>
      </div>
      <div class="order-actions">
        <button type="button" class="primary-button" :disabled="busy" @click="createProduct">
          Create
        </button>
        <button type="button" class="ghost-button" @click="showCreate = false">Cancel</button>
      </div>
    </section>

    <div class="storefront-layout">
      <!-- 分類導覽（index of stock）：桌機側欄 -->
      <aside class="catalog-rail" aria-label="Catalog categories">
        <p class="catalog-rail-label">Catalog</p>
        <button
          type="button"
          :class="['catalog-rail-item', { active: selectedCategory === null }]"
          @click="selectCategory(null)"
        >
          <span>All products</span>
          <b>{{ allProducts.length }}</b>
        </button>
        <button
          v-for="category in categories"
          :key="category.id"
          type="button"
          :class="['catalog-rail-item', { active: selectedCategory === category.id }]"
          @click="selectCategory(category.id)"
        >
          <span>{{ category.name }}</span>
          <b>{{ categoryCounts.get(category.id) ?? 0 }}</b>
        </button>
      </aside>

      <div class="storefront-content">
        <section class="storefront-tools">
          <div class="search-field">
            <Icon name="search" :size="15" />
            <input
              v-model="query"
              type="search"
              placeholder="Search products…"
              aria-label="Search products"
              @keydown.enter="submitSearch"
              @change="submitSearch"
            />
          </div>
          <span v-if="selectedCategory !== null" class="catalog-filter-note">
            {{ categoryName(selectedCategory) }}
            <button type="button" class="text-button" @click="selectCategory(null)">Clear ×</button>
          </span>
        </section>

        <!-- 手機：分類變橫向 chips -->
        <div class="catalog-chips" aria-label="Catalog categories">
          <button
            type="button"
            :class="{ active: selectedCategory === null }"
            @click="selectCategory(null)"
          >
            All
          </button>
          <button
            v-for="category in categories"
            :key="category.id"
            type="button"
            :class="{ active: selectedCategory === category.id }"
            @click="selectCategory(category.id)"
          >
            {{ category.name }}
          </button>
        </div>

        <section v-if="loading" class="product-grid" aria-hidden="true">
          <div v-for="n in PAGE_SIZE" :key="n" class="product-card">
            <div class="product-media"><div class="skeleton-block skeleton-media" /></div>
            <div class="product-foot">
              <div class="skeleton-block skeleton-line" />
              <div class="skeleton-block skeleton-line short" style="margin-left: auto" />
            </div>
            <div class="product-foot">
              <div class="skeleton-block skeleton-line" style="width: 64px" />
            </div>
          </div>
        </section>
        <p v-else-if="loadError" class="empty-state">{{ loadError }}</p>
        <p v-else-if="products.length === 0" class="empty-state">No products found.</p>

        <section v-else class="product-grid" aria-label="Product catalog">
          <article
            v-for="product in products"
            :key="product.id"
            :class="['product-card', { oos: product.stock <= 0 }]"
          >
            <!-- Admin 行內編輯模式 -->
            <div v-if="isAdmin && editingId === product.id" class="product-edit">
              <div class="form-field">
                <input
                  v-model="editForm.name"
                  class="row-edit-field"
                  type="text"
                  placeholder="Name"
                  aria-label="Product name"
                />
                <p v-if="editErrors.name" class="field-error">{{ editErrors.name }}</p>
              </div>
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
              <select
                v-model="editForm.category_id"
                class="filter-select"
                aria-label="Product category"
              >
                <option value="">Uncategorized</option>
                <option
                  v-for="category in categories"
                  :key="category.id"
                  :value="String(category.id)"
                >
                  {{ category.name }}
                </option>
              </select>
              <div class="product-edit-pair">
                <div class="form-field">
                  <input
                    v-model="editForm.price"
                    class="row-edit-field"
                    type="number"
                    step="0.01"
                    min="0"
                    placeholder="Price"
                    aria-label="Product price"
                  />
                  <p v-if="editErrors.price" class="field-error">{{ editErrors.price }}</p>
                </div>
                <div class="form-field">
                  <input
                    v-model="editForm.stock"
                    class="row-edit-field"
                    type="number"
                    min="0"
                    placeholder="Stock"
                    aria-label="Product stock"
                  />
                  <p v-if="editErrors.stock" class="field-error">{{ editErrors.stock }}</p>
                </div>
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
              <!-- 分類 + NEW IN 標籤（NEW IN 由 created_at 真實推導） -->
              <div class="product-tags">
                <span class="tag-stamp cat">{{ categoryName(product.category_id) }}</span>
                <span v-if="isNew(product)" class="tag-stamp new">New in</span>
              </div>
              <div class="product-cart-row">
                <button
                  v-if="product.stock > 0"
                  type="button"
                  class="ghost-button product-add-button"
                  @click="handleAddToCart(product)"
                >
                  <Icon name="cart" :size="14" /> Add to cart
                </button>
                <!-- 零庫存：引導 follow 補貨通知（點擊=追蹤；已追蹤顯示狀態） -->
                <button
                  v-else-if="followedIds[product.id]"
                  type="button"
                  class="ghost-button product-add-button following"
                  disabled
                >
                  <Icon name="star" :size="14" /> Following — restock alert on
                </button>
                <button
                  v-else
                  type="button"
                  class="ghost-button product-add-button notify"
                  @click="toggleFollow(product)"
                >
                  <Icon name="star" :size="14" /> Out of stock — notify me
                </button>
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
      </div>
    </div>

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
</template>
