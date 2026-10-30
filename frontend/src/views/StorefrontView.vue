<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch, type Ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import Icon from "@/components/Icon.vue";
import StorefrontHeader from "@/components/StorefrontHeader.vue";
import StorefrontFooter from "@/components/StorefrontFooter.vue";
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

onUnmounted(() => {
  document.removeEventListener("keydown", onModalKeydown);
  scrollObserver?.disconnect();
});

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

// 排序：空字串 = 不帶 sort 參數（後端維持 id 遞增的預設）。
const sortBy = ref<"" | "newest" | "price_asc" | "price_desc">("");

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
  invalidatePrefetch();
  void fetchProducts();
}

// 排序切換與切分類同一套重置：回第 1 頁 + 作廢在途預取（epoch 防護）。
function selectSort(value: "" | "newest" | "price_asc" | "price_desc"): void {
  if (sortBy.value === value) return;
  sortBy.value = value;
  page.value = 1;
  invalidatePrefetch();
  void fetchProducts();
}

// 後端商品列表無 total 欄位：回滿一頁視為還有下一頁（v1.16 無限滾動）。
const hasMore = ref(true);
const loadingMore = ref(false);

// 列表查詢參數（頁碼 + 搜尋 + 分類 + 排序）：fetch/loadMore/prefetch 共用同一來源。
function listParams(pageNum: number): URLSearchParams {
  const params = new URLSearchParams({
    page: String(pageNum),
    page_size: String(PAGE_SIZE),
  });
  if (appliedQuery.value) params.set("q", appliedQuery.value);
  if (selectedCategory.value !== null) {
    params.set("category_id", String(selectedCategory.value));
  }
  if (sortBy.value) params.set("sort", sortBy.value);
  return params;
}

// ── 投機式預取（v1.17）：第 N 頁落地就背景抓 N+1，捲動觸發時零延遲換入 ──
// 一格快取（只存下一頁）+ epoch 世代防護：搜尋/切分類重置後，
// 在途預取回應屬於舊查詢情境，回來時整包丟棄，不污染新列表。
const prefetched = ref<{ page: number; items: Product[] } | null>(null);
let listEpoch = 0;

function invalidatePrefetch(): void {
  listEpoch += 1;
  prefetched.value = null;
}

async function prefetchNext(): Promise<void> {
  if (prefetched.value !== null || !hasMore.value) return;

  const targetPage = page.value + 1;
  const myEpoch = listEpoch;

  try {
    const items = await api.get(`/products?${listParams(targetPage)}`, ProductListSchema);
    if (myEpoch !== listEpoch) return; // 期間發生重置 → 丟棄
    prefetched.value = { page: targetPage, items };
  } catch {
    // 預取失敗安靜退場：loadMore 會走直接抓的路徑。
  }
}

// 無限滾動：捲到哨兵前 600px 自動載下一頁（append）。
const sentinelEl = ref<HTMLElement | null>(null);

// 骨架卡數量依螢幕寬估算（250px 最小卡寬 + gap），避免小螢幕 overflow
// 或大螢幕只鋪半排的「假加載」感。
const skeletonCount = computed(() => {
  const cols = Math.max(1, Math.floor((window.innerWidth - 80) / 264));
  const rows = Math.max(2, Math.ceil(window.innerHeight / 420));
  return Math.min(PAGE_SIZE, cols * rows);
});
let scrollObserver: IntersectionObserver | undefined;

async function loadMore(): Promise<void> {
  if (loading.value || loadingMore.value || !hasMore.value) return;

  // 快取命中 → 同步換入（投機式預取的回報時刻，使用者零等待）。
  const cached = prefetched.value;
  if (cached !== null && cached.page === page.value + 1) {
    prefetched.value = null; // 先清，防止重複消費
    products.value = [...products.value, ...cached.items];
    page.value += 1;
    // 不足一頁 = 最後一頁（精確停止，避免空批次迴圈）。
    hasMore.value = cached.items.length === PAGE_SIZE;
    void prefetchNext(); // 鏈式：立刻預取下下頁
    return;
  }

  // 快取 miss（重置 race / 預取失敗）→ 直接抓。
  loadingMore.value = true;
  const myEpoch = listEpoch;

  try {
    const next = await api.get(`/products?${listParams(page.value + 1)}`, ProductListSchema);
    if (myEpoch !== listEpoch) return; // 期間重置 → 丟棄，新列表自己管理
    products.value = [...products.value, ...next];
    page.value += 1;
    hasMore.value = next.length === PAGE_SIZE;
  } catch {
    showToast("Failed to load more products.");
    hasMore.value = false;
  } finally {
    loadingMore.value = false;
  }
  void prefetchNext();
}

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

const busy = ref(false);

// 商品 Modal（v1.15）：create/edit 共用，取代展開面板與 inline 卡片編輯。
const productModalOpen = ref(false);
const productModalMode = ref<"create" | "edit">("create");
const editingProduct = ref<Product | null>(null);

const showArchived = ref(false);
const archived = ref<Product[]>([]);
const archivedLoading = ref(false);

const productForm = ref(emptyForm());

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

// zod 表單驗證：錯誤 inline 顯示在欄位下（Modal 內）。
const productErrors = ref<Record<string, string>>({});

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
  const myEpoch = listEpoch;

  try {
    const list = await api.get(`/products?${listParams(page.value)}`, ProductListSchema);
    if (myEpoch !== listEpoch) return; // 期間重置 → 舊回應不覆蓋新列表
    products.value = list;
    hasMore.value = list.length === PAGE_SIZE;
  } catch {
    if (myEpoch === listEpoch) loadError.value = "Failed to load products.";
  } finally {
    if (myEpoch === listEpoch) loading.value = false;
  }

  // 第 1 頁落地 → 背景預取第 2 頁（投機式：不等捲動）。
  void prefetchNext();
}

// 商品/分類變動後同步刷新：列表、分類、計數。
async function refreshCatalog(): Promise<void> {
  await Promise.all([fetchProducts(), fetchCategories(), fetchAllForCounts()]);
}

function submitSearch(): void {
  page.value = 1;
  appliedQuery.value = query.value.trim();
  invalidatePrefetch();
  void fetchProducts();
}

function formatPrice(price: string | number): string {
  return `$${Number(price).toFixed(2)}`;
}

// 卡片 → 詳情頁（v1.18 修 P0「商品卡是死路」）：圖片與名稱可點；星星/加購按鈕 stopPropagation。
function goProduct(product: Product): void {
  void router.push({ name: "product-detail", params: { id: product.id } });
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

function openCreateModal(): void {
  productModalMode.value = "create";
  editingProduct.value = null;
  productForm.value = emptyForm();
  productErrors.value = {};
  productModalOpen.value = true;
}

function openEditModal(product: Product): void {
  productModalMode.value = "edit";
  editingProduct.value = product;
  productForm.value = formFromProduct(product);
  productErrors.value = {};
  productModalOpen.value = true;
}

function closeProductModal(): void {
  productModalOpen.value = false;
  editingProduct.value = null;
}

async function submitProductModal(): Promise<void> {
  const validated = runFormValidation(productForm.value, productErrors);
  if (validated === null) return;
  busy.value = true;

  try {
    if (productModalMode.value === "create") {
      const created = await api.post<Product>("/products", formPayload(validated, productForm.value));
      showToast(`Product "${created.name}" created.`);
      page.value = 1;
    } else if (editingProduct.value) {
      await api.patch(`/products/${editingProduct.value.id}`, formPayload(validated, productForm.value));
      showToast(`Product "${editingProduct.value.name}" updated.`);
    }
    closeProductModal();
    await refreshCatalog();
  } catch (err) {
    const action = productModalMode.value === "create" ? "Create" : "Update";
    showToast(err instanceof ApiError ? `${action} failed: ${err.message}` : `${action} failed.`);
  } finally {
    busy.value = false;
  }
}

function onModalKeydown(event: KeyboardEvent): void {
  if (event.key === "Escape" && productModalOpen.value) closeProductModal();
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
  selectedCategory.value === null ? "Store" : categoryName(selectedCategory.value),
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
      invalidatePrefetch();
      void fetchProducts();
    }
  },
);

// 哨兵帶 v-if（loading 期間不在 DOM）→ 不能在 onMounted 掛 observer；
// watch ref：元素出現時 attach、消失時 detach。
watch(sentinelEl, (el) => {
  scrollObserver?.disconnect();
  if (el && typeof IntersectionObserver !== "undefined") {
    scrollObserver = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) void loadMore();
      },
      // 提前 600px 觸發：使用者還沒到底，下一頁已在路上。
      { rootMargin: "600px" },
    );
    scrollObserver.observe(el);
  }
});

onMounted(() => {
  document.addEventListener("keydown", onModalKeydown);
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
        <button type="button" class="primary-button" @click="openCreateModal">
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
          <select
            class="filter-select"
            aria-label="Sort products"
            :value="sortBy"
            @change="selectSort(($event.target as HTMLSelectElement).value as '' | 'newest' | 'price_asc' | 'price_desc')"
          >
            <option value="">Sort: Default</option>
            <option value="newest">Newest first</option>
            <option value="price_asc">Price: low to high</option>
            <option value="price_desc">Price: high to low</option>
          </select>
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
          <div
            v-for="n in skeletonCount"
            :key="n"
            class="product-card skeleton-card"
            :style="{ animationDelay: `${(n - 1) * 0.04}s` }"
          >
            <div class="product-media"><div class="skeleton-block skeleton-media" /></div>
            <div class="product-foot">
              <div class="skeleton-block skeleton-line" />
              <div class="skeleton-block skeleton-line short" style="margin-left: auto" />
            </div>
            <div class="product-tags">
              <div class="skeleton-block skeleton-line" style="width: 72px" />
              <div class="skeleton-block skeleton-line" style="width: 44px" />
            </div>
            <div class="product-cart-row">
              <div class="skeleton-block skeleton-line" style="width: 100%; height: 34px" />
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
                  <div class="product-media" @click="goProduct(product)">
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
                  @click.stop="toggleFollow(product)"
                >
                  <Icon name="star" :size="15" />
                </button>
                <button
                  v-else
                  type="button"
                  class="follow-star"
                  :aria-label="`Sign in to follow ${product.name}`"
                  @click.stop="toggleFollow(product)"
                >
                  <Icon name="star" :size="15" />
                </button>
              </div>
              <div class="product-foot">
                <router-link
                  class="product-name"
                  :to="{ name: 'product-detail', params: { id: product.id } }"
                  :title="product.name"
                >
                  {{ product.name }}
                </router-link>
                <!-- 描述吃滿整行（298px > 最長描述 190px）：名稱不再與描述搶位，零截斷 -->
                <span v-if="product.description" class="product-desc" :title="product.description">
                  {{ product.description }}
                </span>
                <div class="product-meta">
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
                <button type="button" class="sort-button" @click="openEditModal(product)">Edit</button>
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
          </article>
        </section>

        <!-- 無限滾動：載入中顯示延續格線的骨架卡；閒置顯示計數與 Load more -->
        <template v-if="!loading && products.length > 0">
          <section v-if="loadingMore" class="product-grid" aria-hidden="true">
            <div v-for="n in skeletonCount" :key="`more-${n}`" class="product-card skeleton-card">
              <div class="product-media"><div class="skeleton-block skeleton-media" /></div>
              <div class="product-foot">
                <div class="skeleton-block skeleton-line" />
                <div class="skeleton-block skeleton-line short" style="margin-left: auto" />
              </div>
              <div class="product-tags">
                <div class="skeleton-block skeleton-line" style="width: 72px" />
              </div>
            </div>
          </section>
          <div ref="sentinelEl" class="infinite-sentinel">
            <button v-if="hasMore && !loadingMore" type="button" class="ghost-button" @click="loadMore">
              Load more
            </button>
            <p v-else-if="!hasMore" class="infinite-end">
              End of catalog · {{ products.length }} product{{ products.length === 1 ? "" : "s" }}
            </p>
          </div>
        </template>
    </div>
    </div>

    <!-- 商品 Modal（create / edit 共用） -->
    <Teleport to="body">
      <div v-if="isAdmin && productModalOpen" class="modal-overlay" @click.self="closeProductModal">
        <div
          class="modal product-modal"
          role="dialog"
          aria-modal="true"
          :aria-label="productModalMode === 'create' ? 'New product' : 'Edit product'"
        >
          <div class="modal-header">
            <h3>{{ productModalMode === "create" ? "New product" : `Edit "${editingProduct?.name}"` }}</h3>
            <button type="button" class="row-action" aria-label="Close dialog" @click="closeProductModal">
              <Icon name="close" :size="15" />
            </button>
          </div>
          <div class="modal-body product-modal-fields">
            <div class="form-field">
              <label class="account-label" for="p-name">Name</label>
              <input id="p-name" v-model="productForm.name" class="row-edit-field" type="text" placeholder="Name" aria-label="Product name" />
              <p v-if="productErrors.name" class="field-error">{{ productErrors.name }}</p>
            </div>
            <div class="form-field">
              <label class="account-label" for="p-desc">Description</label>
              <input id="p-desc" v-model="productForm.description" class="row-edit-field" type="text" placeholder="Description (optional)" aria-label="Product description" />
            </div>
            <div class="form-field">
              <label class="account-label" for="p-image">Image URL</label>
              <input id="p-image" v-model="productForm.image_url" class="row-edit-field" type="text" placeholder="https://…" aria-label="Product image URL" />
            </div>
            <div class="product-modal-pair">
              <div class="form-field">
                <label class="account-label" for="p-cat">Category</label>
                <select id="p-cat" v-model="productForm.category_id" class="filter-select" aria-label="Product category">
                  <option value="">Uncategorized</option>
                  <option v-for="category in categories" :key="category.id" :value="String(category.id)">
                    {{ category.name }}
                  </option>
                </select>
              </div>
              <div class="form-field">
                <label class="account-label" for="p-price">Price</label>
                <input id="p-price" v-model="productForm.price" class="row-edit-field" type="number" step="0.01" min="0" placeholder="0.00" aria-label="Product price" />
                <p v-if="productErrors.price" class="field-error">{{ productErrors.price }}</p>
              </div>
              <div class="form-field">
                <label class="account-label" for="p-stock">Stock</label>
                <input id="p-stock" v-model="productForm.stock" class="row-edit-field" type="number" min="0" placeholder="0" aria-label="Product stock" />
                <p v-if="productErrors.stock" class="field-error">{{ productErrors.stock }}</p>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="ghost-button" @click="closeProductModal">Cancel</button>
            <button type="button" class="primary-button" :disabled="busy" @click="submitProductModal">
              {{ productModalMode === "create" ? "Create" : "Save changes" }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

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

  <StorefrontFooter />
</template>
