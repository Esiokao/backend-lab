<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch, type Ref } from "vue";

import Icon from "@/components/Icon.vue";
import { ApiError, api } from "@/lib/api";
import {
  CategoryPageSchema,
  ProductFormSchema,
  ProductListSchema,
  type Category,
  type Product,
} from "@/lib/schemas";
import { useToast } from "@/stores/toast";

// Admin 商品管理（Product Management）：
// 支援 Active / Archived 分頁標籤切換、搜尋、分類篩選、新增/編輯/封存/復原/刪除商品。
// Modal 點擊外部遮罩不關閉，保持表單安全。

type ProductForm = {
  name: string;
  description: string;
  image_url: string;
  price: string;
  stock: string;
  category_id: string; // 空字串 = 未分類
};

const PAGE_SIZE = 12;
const toast = useToast();

const currentTab = ref<"active" | "archived">("active");

// 縮圖大小切換（small / large），支援 localStorage 記憶偏好
const imageSize = ref<"small" | "large">(
  (localStorage.getItem("admin_product_thumb_size") as "small" | "large") || "large",
);

function setImageSize(size: "small" | "large"): void {
  imageSize.value = size;
  localStorage.setItem("admin_product_thumb_size", size);
}

// Active 商品狀態
const activeProducts = ref<Product[]>([]);
const allActiveProducts = ref<Product[]>([]);
const activeLoading = ref(true);
const activePage = ref(1);
const activeQuery = ref("");
const appliedQuery = ref("");
const selectedCategory = ref<number | null>(null);
const activeHasMore = ref(true);

// Archived 商品狀態
const archivedProducts = ref<Product[]>([]);
const archivedLoading = ref(false);
const archivedQuery = ref("");

const totalActiveCount = computed(() => allActiveProducts.value.length);
const totalArchivedCount = computed(() => archivedProducts.value.length);
const grandTotalCount = computed(() => totalActiveCount.value + totalArchivedCount.value);

// 分類與共用
const categories = ref<Category[]>([]);
const busy = ref(false);
const brokenImages = ref<Record<number, boolean>>({});

function onImageError(productId: number): void {
  brokenImages.value[productId] = true;
}

const categoryMap = computed(() => new Map(categories.value.map((c) => [c.id, c])));

function categoryName(id: number | null): string {
  return id === null ? "Uncategorized" : (categoryMap.value.get(id)?.name ?? "Uncategorized");
}

const currentCategoryName = computed(() => {
  if (selectedCategory.value === null) return "All categories";
  return categoryMap.value.get(selectedCategory.value)?.name ?? "All categories";
});

function formatPrice(price: string | number): string {
  return `$${Number(price).toFixed(2)}`;
}

// ── 取得分類 ──
async function fetchCategories(): Promise<void> {
  try {
    const data = await api.get("/categories", CategoryPageSchema);
    categories.value = data.items;
  } catch {
    // 忽略分類載入失敗
  }
}

// ── Active 商品撈取 ──
async function fetchActiveProducts(): Promise<void> {
  activeLoading.value = true;
  try {
    const params = new URLSearchParams({
      page: String(activePage.value),
      page_size: String(PAGE_SIZE),
    });
    if (appliedQuery.value) params.set("q", appliedQuery.value);
    if (selectedCategory.value !== null) params.set("category_id", String(selectedCategory.value));

    const list = await api.get(`/products?${params.toString()}`, ProductListSchema);
    activeProducts.value = list;
    activeHasMore.value = list.length === PAGE_SIZE;
  } catch (err) {
    toast.show(err instanceof ApiError ? `Failed to load products: ${err.message}` : "Failed to load products.");
  } finally {
    activeLoading.value = false;
  }
}

async function fetchAllActiveCount(): Promise<void> {
  try {
    allActiveProducts.value = await api.get("/products?page_size=100", ProductListSchema);
  } catch {
    // 忽略計數載入失敗
  }
}

function submitActiveSearch(): void {
  activePage.value = 1;
  appliedQuery.value = activeQuery.value.trim();
  void fetchActiveProducts();
}

function onCategoryChange(): void {
  activePage.value = 1;
  void fetchActiveProducts();
}

// ── Archived 商品撈取 ──
async function fetchArchivedProducts(): Promise<void> {
  archivedLoading.value = true;
  try {
    archivedProducts.value = await api.get<Product[]>("/products/archived");
  } catch (err) {
    toast.show(
      err instanceof ApiError
        ? `Failed to load archived products: ${err.message}`
        : "Failed to load archived products.",
    );
  } finally {
    archivedLoading.value = false;
  }
}

const filteredArchived = computed(() => {
  const q = archivedQuery.value.trim().toLowerCase();
  if (!q) return archivedProducts.value;
  return archivedProducts.value.filter(
    (p) =>
      p.name.toLowerCase().includes(q) ||
      (p.description && p.description.toLowerCase().includes(q)),
  );
});

// 切換 Tab
function switchTab(tab: "active" | "archived"): void {
  currentTab.value = tab;
  if (tab === "archived") {
    void fetchArchivedProducts();
  } else {
    void fetchActiveProducts();
  }
}

// ── 商品 CRUD Modal ──
const productModalOpen = ref(false);
const productModalMode = ref<"create" | "edit">("create");
const editingProduct = ref<Product | null>(null);
const productForm = ref<ProductForm>(emptyForm());
const productErrors = ref<Record<string, string>>({});

function emptyForm(): ProductForm {
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

function openCreateModal(): void {
  productModalMode.value = "create";
  editingProduct.value = null;
  productForm.value = emptyForm();
  if (selectedCategory.value !== null) {
    productForm.value.category_id = String(selectedCategory.value);
  }
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

async function submitProductModal(): Promise<void> {
  const validated = runFormValidation(productForm.value, productErrors);
  if (validated === null) return;
  busy.value = true;

  try {
    if (productModalMode.value === "create") {
      const created = await api.post<Product>("/products", formPayload(validated, productForm.value));
      toast.show(`Product "${created.name}" created.`);
      activePage.value = 1;
    } else if (editingProduct.value) {
      await api.patch(`/products/${editingProduct.value.id}`, formPayload(validated, productForm.value));
      toast.show(`Product "${editingProduct.value.name}" updated.`);
    }
    closeProductModal();
    await fetchActiveProducts();
    await fetchAllActiveCount();
  } catch (err) {
    const action = productModalMode.value === "create" ? "Create" : "Update";
    toast.show(err instanceof ApiError ? `${action} failed: ${err.message}` : `${action} failed.`);
  } finally {
    busy.value = false;
  }
}

async function archiveProduct(product: Product): Promise<void> {
  busy.value = true;
  try {
    await api.patch(`/products/${product.id}/archive`, {});
    toast.show(`Product "${product.name}" archived.`);
    await fetchActiveProducts();
    await fetchAllActiveCount();
    await fetchArchivedProducts();
  } catch (err) {
    toast.show(err instanceof ApiError ? `Archive failed: ${err.message}` : "Archive failed.");
  } finally {
    busy.value = false;
  }
}

async function restoreProduct(product: Product): Promise<void> {
  busy.value = true;
  try {
    await api.patch(`/products/${product.id}/restore`, {});
    toast.show(`Product "${product.name}" restored.`);
    await fetchArchivedProducts();
    await fetchAllActiveCount();
  } catch (err) {
    toast.show(err instanceof ApiError ? `Restore failed: ${err.message}` : "Restore failed.");
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
    toast.show(`Product "${product.name}" deleted.`);
    if (currentTab.value === "active") {
      await fetchActiveProducts();
    } else {
      await fetchArchivedProducts();
    }
    await fetchAllActiveCount();
  } catch (err) {
    toast.show(err instanceof ApiError ? `Delete failed: ${err.message}` : "Delete failed.");
  } finally {
    busy.value = false;
  }
}

function onModalKeydown(event: KeyboardEvent): void {
  if (event.key === "Escape" && productModalOpen.value) closeProductModal();
}

onMounted(() => {
  document.addEventListener("keydown", onModalKeydown);
  void fetchCategories();
  void fetchActiveProducts();
  void fetchAllActiveCount();
  void fetchArchivedProducts();
});

onUnmounted(() => {
  document.removeEventListener("keydown", onModalKeydown);
});

watch(activePage, () => void fetchActiveProducts());
</script>

<template>
  <section class="page-heading">
    <div class="th-main">
      <h1>Product Management</h1>
      <p>Manage catalog products, pricing, inventory, and archive status</p>
      <p class="admin-prod-submeta">
        <strong>{{ currentCategoryName }}</strong>
        <template v-if="!activeLoading"> · <strong>{{ grandTotalCount }}</strong> total products</template>
      </p>
    </div>
    <div class="th-cell"><small>Sheet</small><b>ADMIN-PRD-01</b></div>
  </section>

  <!-- Tab 切換：Active / Archived -->
  <div class="admin-tabs" style="display: flex; gap: 8px; margin-top: 16px;">
    <button
      type="button"
      :class="['admin-tab-btn', { active: currentTab === 'active' }]"
      @click="switchTab('active')"
    >
      Active products
      <span class="tab-count-badge">{{ totalActiveCount }}</span>
    </button>
    <button
      type="button"
      :class="['admin-tab-btn', { active: currentTab === 'archived' }]"
      @click="switchTab('archived')"
    >
      Archived products
      <span class="tab-count-badge">{{ totalArchivedCount }}</span>
    </button>
  </div>

  <!-- Active Products Panel -->
  <section v-if="currentTab === 'active'" class="data-panel" aria-label="Active products">
    <div class="panel-header">
      <div>
        <h2>Active products</h2>
        <p>
          {{ totalActiveCount }} active product{{ totalActiveCount === 1 ? "" : "s" }} currently visible in storefront.
        </p>
      </div>
      <div class="panel-actions">
        <label class="search-field">
          <Icon name="search" :size="15" />
          <input
            v-model="activeQuery"
            type="search"
            placeholder="Search products…"
            aria-label="Search products"
            @keydown.enter="submitActiveSearch"
            @change="submitActiveSearch"
          />
        </label>
        <select
          v-model="selectedCategory"
          class="filter-select"
          aria-label="Filter by category"
          @change="onCategoryChange"
        >
          <option :value="null">All categories</option>
          <option v-for="category in categories" :key="category.id" :value="category.id">
            {{ category.name }}
          </option>
        </select>
        <div class="view-size-group" style="display: flex; border: 1px solid var(--line); border-radius: 7px; overflow: hidden; background: var(--card);">
          <button
            type="button"
            :class="['sort-button', { active: imageSize === 'small' }]"
            :style="imageSize === 'small' ? 'border: 0; border-radius: 0; background: var(--cream); color: var(--ink-strong); font-weight: 600;' : 'border: 0; border-radius: 0; background: transparent;'"
            title="Small image"
            aria-label="Small image view"
            @click="setImageSize('small')"
          >
            Small
          </button>
          <button
            type="button"
            :class="['sort-button', { active: imageSize === 'large' }]"
            :style="imageSize === 'large' ? 'border: 0; border-radius: 0; background: var(--cream); color: var(--ink-strong); font-weight: 600;' : 'border: 0; border-radius: 0; background: transparent; border-left: 1px solid var(--line);'"
            title="Large image"
            aria-label="Large image view"
            @click="setImageSize('large')"
          >
            Large
          </button>
        </div>
        <button type="button" class="primary-button" @click="openCreateModal">
          <Icon name="plus" :size="15" /> New product
        </button>
      </div>
    </div>

    <div class="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Product</th>
            <th>Category</th>
            <th>Price</th>
            <th>Stock</th>
            <th><span class="sr-only">Actions</span></th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!activeLoading && activeProducts.length === 0">
            <td colspan="5"><p class="empty-state">No products found.</p></td>
          </tr>
          <tr v-for="product in activeProducts" :key="product.id">
            <td>
              <div class="admin-prod-cell">
                <div :class="['admin-prod-thumb', imageSize]">
                  <img
                    v-if="product.image_url && !brokenImages[product.id]"
                    :src="product.image_url"
                    :alt="product.name"
                    loading="lazy"
                    @error="onImageError(product.id)"
                  />
                  <Icon v-else name="box" :size="imageSize === 'large' ? 30 : 20" />
                </div>
                <div class="admin-prod-info">
                  <strong>{{ product.name }}</strong>
                  <small v-if="product.description" style="display: block; color: var(--ink-faint); font-size: 11px;">
                    {{ product.description }}
                  </small>
                </div>
              </div>
            </td>
            <td><span class="order-date">{{ categoryName(product.category_id) }}</span></td>
            <td><span class="product-price">{{ formatPrice(product.price) }}</span></td>
            <td>
              <span :style="product.stock <= 0 ? 'color: var(--danger); font-weight: 600;' : ''">
                {{ product.stock }}
              </span>
            </td>
            <td>
              <div class="order-actions">
                <button type="button" class="sort-button" @click="openEditModal(product)">
                  Edit
                </button>
                <button
                  type="button"
                  class="sort-button"
                  :disabled="busy"
                  @click="archiveProduct(product)"
                >
                  Archive
                </button>
                <button
                  type="button"
                  class="row-action row-delete"
                  :aria-label="`Delete ${product.name}`"
                  :disabled="busy"
                  @click="deleteProduct(product)"
                >
                  <Icon name="close" :size="14" />
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="activeLoading" class="empty-state">Loading products…</p>
    </div>

    <div class="pagination">
      <p>
        Page <strong>{{ activePage }}</strong>
        <template v-if="appliedQuery"> · matching "{{ appliedQuery }}"</template>
      </p>
      <div>
        <button :disabled="activePage <= 1" @click="activePage -= 1">Previous</button>
        <button :disabled="!activeHasMore" @click="activePage += 1">Next</button>
      </div>
    </div>
  </section>

  <!-- Archived Products Panel -->
  <section v-else class="data-panel" aria-label="Archived products">
    <div class="panel-header">
      <div>
        <h2>Archived products</h2>
        <p>
          {{ totalArchivedCount }} archived product{{ totalArchivedCount === 1 ? "" : "s" }} hidden from storefront. Restore to put them back on shelf.
        </p>
      </div>
      <div class="panel-actions">
        <label class="search-field">
          <Icon name="search" :size="15" />
          <input
            v-model="archivedQuery"
            type="search"
            placeholder="Search archived…"
            aria-label="Search archived products"
          />
        </label>
        <div class="view-size-group" style="display: flex; border: 1px solid var(--line); border-radius: 7px; overflow: hidden; background: var(--card);">
          <button
            type="button"
            :class="['sort-button', { active: imageSize === 'small' }]"
            :style="imageSize === 'small' ? 'border: 0; border-radius: 0; background: var(--cream); color: var(--ink-strong); font-weight: 600;' : 'border: 0; border-radius: 0; background: transparent;'"
            title="Small image"
            aria-label="Small image view"
            @click="setImageSize('small')"
          >
            Small
          </button>
          <button
            type="button"
            :class="['sort-button', { active: imageSize === 'large' }]"
            :style="imageSize === 'large' ? 'border: 0; border-radius: 0; background: var(--cream); color: var(--ink-strong); font-weight: 600;' : 'border: 0; border-radius: 0; background: transparent; border-left: 1px solid var(--line);'"
            title="Large image"
            aria-label="Large image view"
            @click="setImageSize('large')"
          >
            Large
          </button>
        </div>
      </div>
    </div>

    <div class="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Product</th>
            <th>Category</th>
            <th>Price</th>
            <th>Stock</th>
            <th><span class="sr-only">Actions</span></th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!archivedLoading && filteredArchived.length === 0">
            <td colspan="5"><p class="empty-state">No archived products found.</p></td>
          </tr>
          <tr v-for="product in filteredArchived" :key="product.id">
            <td>
              <div class="admin-prod-cell">
                <div :class="['admin-prod-thumb', imageSize]">
                  <img
                    v-if="product.image_url && !brokenImages[product.id]"
                    :src="product.image_url"
                    :alt="product.name"
                    loading="lazy"
                    @error="onImageError(product.id)"
                  />
                  <Icon v-else name="box" :size="imageSize === 'large' ? 30 : 20" />
                </div>
                <div class="admin-prod-info">
                  <strong>{{ product.name }}</strong>
                  <small v-if="product.description" style="display: block; color: var(--ink-faint); font-size: 11px;">
                    {{ product.description }}
                  </small>
                </div>
              </div>
            </td>
            <td><span class="order-date">{{ categoryName(product.category_id) }}</span></td>
            <td><span class="product-price">{{ formatPrice(product.price) }}</span></td>
            <td>{{ product.stock }}</td>
            <td>
              <div class="order-actions">
                <button
                  type="button"
                  class="sort-button"
                  :disabled="busy"
                  @click="restoreProduct(product)"
                >
                  Restore
                </button>
                <button
                  type="button"
                  class="row-action row-delete"
                  :aria-label="`Delete ${product.name}`"
                  :disabled="busy"
                  @click="deleteProduct(product)"
                >
                  <Icon name="close" :size="14" />
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="archivedLoading" class="empty-state">Loading archived products…</p>
    </div>
  </section>

  <!-- 商品 Modal（create / edit 共用） -->
  <Teleport to="body">
    <div v-if="productModalOpen" class="modal-overlay">
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
            <input
              id="p-name"
              v-model="productForm.name"
              class="row-edit-field"
              type="text"
              placeholder="Name"
              aria-label="Product name"
            />
            <p v-if="productErrors.name" class="field-error">{{ productErrors.name }}</p>
          </div>
          <div class="form-field">
            <label class="account-label" for="p-desc">Description</label>
            <input
              id="p-desc"
              v-model="productForm.description"
              class="row-edit-field"
              type="text"
              placeholder="Description (optional)"
              aria-label="Product description"
            />
          </div>
          <div class="form-field">
            <label class="account-label" for="p-img">Image URL</label>
            <input
              id="p-img"
              v-model="productForm.image_url"
              class="row-edit-field"
              type="url"
              placeholder="https://example.com/item.jpg (optional)"
              aria-label="Product image URL"
            />
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
              <input
                id="p-price"
                v-model="productForm.price"
                class="row-edit-field"
                type="number"
                step="0.01"
                min="0"
                placeholder="0.00"
                aria-label="Product price"
              />
              <p v-if="productErrors.price" class="field-error">{{ productErrors.price }}</p>
            </div>
            <div class="form-field">
              <label class="account-label" for="p-stock">Stock</label>
              <input
                id="p-stock"
                v-model="productForm.stock"
                class="row-edit-field"
                type="number"
                min="0"
                placeholder="0"
                aria-label="Product stock"
              />
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
</template>
