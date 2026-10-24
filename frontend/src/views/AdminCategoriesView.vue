<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";

import Icon from "@/components/Icon.vue";
import { ApiError, api } from "@/lib/api";
import { CategoryPageSchema, type Category } from "@/lib/schemas";
import { useToast } from "@/stores/toast";

// Admin 分類管理（v1.13）：
// - New category 按鈕在面板 header（標題塊保持純標題）
// - 搜尋（q）+ 分頁（server-side page/page_size/total）
// - Edit 以 Modal 進行（不再行內編輯）

type Product = {
  id: number;
  name: string;
  category_id: number | null;
};

const PAGE_SIZE = 10;

const toast = useToast();

const categories = ref<Category[]>([]);
const products = ref<Product[]>([]);
const total = ref(0);
const page = ref(1);
const query = ref("");
const appliedQuery = ref("");
const loading = ref(true);
const loadError = ref("");
const busy = ref(false);

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)));
const hasNext = computed(() => page.value < totalPages.value);

// 各分類商品數（未分類單獨算給合計列）。
function productCount(categoryId: number): number {
  return products.value.filter((p) => p.category_id === categoryId).length;
}

const uncategorizedCount = () =>
  products.value.filter((p) => p.category_id === null).length;

async function load(): Promise<void> {
  loading.value = true;
  loadError.value = "";

  try {
    const params = new URLSearchParams({
      page: String(page.value),
      page_size: String(PAGE_SIZE),
    });
    if (appliedQuery.value) params.set("q", appliedQuery.value);

    const [catData, prodData] = await Promise.all([
      api.get(`/categories?${params.toString()}`, CategoryPageSchema),
      api.get("/products?page_size=100"),
    ]);
    categories.value = catData.items;
    total.value = catData.total;
    products.value = prodData as Product[];
  } catch (err) {
    loadError.value =
      err instanceof ApiError ? `Failed to load: ${err.message}` : "Failed to load categories.";
  } finally {
    loading.value = false;
  }
}

function submitSearch(): void {
  page.value = 1;
  appliedQuery.value = query.value.trim();
  void load();
}

watch(page, () => void load());

// ── Modal（create / edit 共用）──
const modalOpen = ref(false);
const modalMode = ref<"create" | "edit">("create");
const editingCategory = ref<Category | null>(null);
const form = ref({ name: "", description: "" });

function openCreate(): void {
  modalMode.value = "create";
  editingCategory.value = null;
  form.value = { name: "", description: "" };
  modalOpen.value = true;
}

function openEdit(category: Category): void {
  modalMode.value = "edit";
  editingCategory.value = category;
  form.value = { name: category.name, description: category.description ?? "" };
  modalOpen.value = true;
}

function closeModal(): void {
  modalOpen.value = false;
  editingCategory.value = null;
}

async function saveModal(): Promise<void> {
  const name = form.value.name.trim();
  if (!name) {
    toast.show("Category name is required.");
    return;
  }

  busy.value = true;
  try {
    if (modalMode.value === "create") {
      await api.post("/categories", { name, description: form.value.description.trim() || null });
      toast.show(`Category "${name}" created.`);
      // 新建後回第一頁（新分類 id 最大、在尾頁）。
      page.value = 1;
      appliedQuery.value = "";
      query.value = "";
      await load();
    } else if (editingCategory.value) {
      await api.patch(`/categories/${editingCategory.value.id}`, {
        name,
        description: form.value.description.trim() || null,
      });
      toast.show(`Category "${name}" updated.`);
      await load();
    }
    closeModal();
  } catch (err) {
    toast.show(err instanceof ApiError ? `Save failed: ${err.message}` : "Save failed.");
  } finally {
    busy.value = false;
  }
}

async function deleteCategory(category: Category): Promise<void> {
  const count = productCount(category.id);
  const warning =
    count > 0
      ? `Delete "${category.name}"? ${count} product${count === 1 ? "" : "s"} will become uncategorized.`
      : `Delete "${category.name}"?`;

  if (!window.confirm(warning)) return;

  busy.value = true;
  try {
    await api.delete(`/categories/${category.id}`);
    toast.show(`Category "${category.name}" deleted.`);
    // 刪除後總頁數可能縮水 → 收回。
    if (page.value > totalPages.value) page.value = totalPages.value;
    await load();
  } catch (err) {
    toast.show(err instanceof ApiError ? `Delete failed: ${err.message}` : "Delete failed.");
  } finally {
    busy.value = false;
  }
}

function onModalKeydown(event: KeyboardEvent): void {
  if (event.key === "Escape") closeModal();
}

onMounted(() => {
  document.addEventListener("keydown", onModalKeydown);
  void load();
});
</script>

<template>
  <section class="page-heading">
    <div class="th-main">
      <h1>Category Management</h1>
      <p>Organize the catalog. Deleting a category leaves its products uncategorized.</p>
    </div>
    <div class="th-cell"><small>Sheet</small><b>ADMIN-CAT-01</b></div>
  </section>

  <section class="data-panel">
    <div class="panel-header">
      <div>
        <h2>Categories</h2>
        <p>
          {{ total }} categor{{ total === 1 ? "y" : "ies" }} ·
          {{ uncategorizedCount() }} uncategorized product{{ uncategorizedCount() === 1 ? "" : "s" }}
        </p>
      </div>
      <div class="panel-actions">
        <label class="search-field">
          <Icon name="search" :size="15" />
          <input
            v-model="query"
            type="search"
            placeholder="Search categories…"
            aria-label="Search categories"
            @keydown.enter="submitSearch"
            @change="submitSearch"
          />
        </label>
        <button type="button" class="primary-button" @click="openCreate">
          <Icon name="plus" :size="15" /> New category
        </button>
      </div>
    </div>

    <div class="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Name</th>
            <th>Description</th>
            <th>Products</th>
            <th><span class="sr-only">Actions</span></th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!loading && categories.length === 0">
            <td colspan="4"><p class="empty-state">No categories found.</p></td>
          </tr>
          <tr v-for="category in categories" :key="category.id">
            <td><strong>{{ category.name }}</strong></td>
            <td><span class="order-date">{{ category.description ?? "—" }}</span></td>
            <td><span class="order-total">{{ productCount(category.id) }}</span></td>
            <td>
              <div class="order-actions">
                <button type="button" class="sort-button" @click="openEdit(category)">
                  Edit
                </button>
                <button
                  type="button"
                  class="row-action row-delete"
                  :aria-label="`Delete ${category.name}`"
                  :disabled="busy"
                  @click="deleteCategory(category)"
                >
                  <Icon name="close" :size="14" />
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="loading" class="empty-state">Loading categories...</p>
      <p v-else-if="loadError" class="empty-state">{{ loadError }}</p>
    </div>

    <div class="pagination">
      <p>
        Page <strong>{{ page }}</strong> of <strong>{{ totalPages }}</strong>
        <template v-if="appliedQuery"> · matching "{{ appliedQuery }}"</template>
      </p>
      <div>
        <button :disabled="page <= 1" @click="page -= 1">Previous</button>
        <button :disabled="!hasNext" @click="page += 1">Next</button>
      </div>
    </div>
  </section>

  <!-- Modal：create / edit -->
  <Teleport to="body">
    <div v-if="modalOpen" class="modal-overlay" @click.self="closeModal">
      <div class="modal" role="dialog" aria-modal="true" :aria-label="modalMode === 'create' ? 'New category' : 'Edit category'">
        <div class="modal-header">
          <h3>{{ modalMode === "create" ? "New category" : `Edit "${editingCategory?.name}"` }}</h3>
          <button type="button" class="row-action" aria-label="Close dialog" @click="closeModal">
            <Icon name="close" :size="15" />
          </button>
        </div>
        <div class="modal-body">
          <label class="account-label" for="category-name">Name</label>
          <input
            id="category-name"
            v-model="form.name"
            class="row-edit-field"
            type="text"
            placeholder="Category name"
            aria-label="Category name"
          />
          <label class="account-label" for="category-description">Description</label>
          <input
            id="category-description"
            v-model="form.description"
            class="row-edit-field"
            type="text"
            placeholder="Description (optional)"
            aria-label="Category description"
          />
        </div>
        <div class="modal-footer">
          <button type="button" class="ghost-button" @click="closeModal">Cancel</button>
          <button type="button" class="primary-button" :disabled="busy" @click="saveModal">
            {{ modalMode === "create" ? "Create" : "Save changes" }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
