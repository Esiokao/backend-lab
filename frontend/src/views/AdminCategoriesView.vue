<script setup lang="ts">
import { onMounted, ref } from "vue";

import Icon from "@/components/Icon.vue";
import { ApiError, api } from "@/lib/api";
import { useToast } from "@/stores/toast";

// Admin 分類管理（v1.6）：/categories CRUD 的管理頁。
// 刪除分類 → 後端將該分類商品 category_id 設為 NULL（未分類），confirm 會先警告受影響數。

type Category = {
  id: number;
  name: string;
  description: string | null;
};

type Product = {
  id: number;
  name: string;
  category_id: number | null;
};

const toast = useToast();

const categories = ref<Category[]>([]);
const products = ref<Product[]>([]);
const loading = ref(true);
const loadError = ref("");
const busy = ref(false);

const showCreate = ref(false);
const createForm = ref({ name: "", description: "" });

const editingId = ref<number | null>(null);
const editForm = ref({ name: "", description: "" });

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
    const [cats, prods] = await Promise.all([
      api.get<Category[]>("/categories"),
      api.get<Product[]>("/products?page_size=100"),
    ]);
    categories.value = cats;
    products.value = prods;
  } catch (err) {
    loadError.value =
      err instanceof ApiError ? `Failed to load: ${err.message}` : "Failed to load categories.";
  } finally {
    loading.value = false;
  }
}

async function createCategory(): Promise<void> {
  const name = createForm.value.name.trim();
  if (!name) {
    toast.show("Category name is required.");
    return;
  }

  busy.value = true;
  try {
    await api.post("/categories", {
      name,
      description: createForm.value.description.trim() || null,
    });
    createForm.value = { name: "", description: "" };
    showCreate.value = false;
    toast.show(`Category "${name}" created.`);
    await load();
  } catch (err) {
    toast.show(err instanceof ApiError ? `Create failed: ${err.message}` : "Create failed.");
  } finally {
    busy.value = false;
  }
}

function startEdit(category: Category): void {
  editingId.value = category.id;
  editForm.value = { name: category.name, description: category.description ?? "" };
}

function cancelEdit(): void {
  editingId.value = null;
}

async function saveEdit(category: Category): Promise<void> {
  const name = editForm.value.name.trim();
  if (!name) {
    toast.show("Category name is required.");
    return;
  }

  busy.value = true;
  try {
    await api.patch(`/categories/${category.id}`, {
      name,
      description: editForm.value.description.trim() || null,
    });
    editingId.value = null;
    toast.show(`Category "${name}" updated.`);
    await load();
  } catch (err) {
    toast.show(err instanceof ApiError ? `Update failed: ${err.message}` : "Update failed.");
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
    await load();
  } catch (err) {
    toast.show(err instanceof ApiError ? `Delete failed: ${err.message}` : "Delete failed.");
  } finally {
    busy.value = false;
  }
}

onMounted(load);
</script>

<template>
  <section class="page-heading">
    <div class="th-main">
      <h1>Category Management</h1>
      <p>Organize the catalog. Deleting a category leaves its products uncategorized.</p>
    </div>
    <button
      type="button"
      class="primary-button"
      @click="showCreate = !showCreate"
    >
      <Icon name="plus" :size="15" /> New category
    </button>
    <div class="th-cell"><small>Sheet</small><b>ADMIN-CAT-01</b></div>
  </section>

  <section v-if="showCreate" class="product-create-panel" aria-label="New category">
    <h2>New category</h2>
    <div class="product-create-fields">
      <input
        v-model="createForm.name"
        class="row-edit-field"
        type="text"
        placeholder="Name"
        aria-label="Category name"
      />
      <input
        v-model="createForm.description"
        class="row-edit-field"
        type="text"
        placeholder="Description (optional)"
        aria-label="Category description"
      />
    </div>
    <div class="order-actions">
      <button type="button" class="primary-button" :disabled="busy" @click="createCategory">
        Create
      </button>
      <button type="button" class="ghost-button" @click="showCreate = false">Cancel</button>
    </div>
  </section>

  <section class="data-panel">
    <div class="panel-header">
      <div>
        <h2>Categories</h2>
        <p>
          {{ categories.length }} categor{{ categories.length === 1 ? "y" : "ies" }} ·
          {{ uncategorizedCount() }} uncategorized product{{ uncategorizedCount() === 1 ? "" : "s" }}
        </p>
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
            <td colspan="4"><p class="empty-state">No categories yet.</p></td>
          </tr>
          <tr v-for="category in categories" :key="category.id">
            <template v-if="editingId === category.id">
              <td>
                <input
                  v-model="editForm.name"
                  class="row-edit-field"
                  type="text"
                  aria-label="Category name"
                />
              </td>
              <td>
                <input
                  v-model="editForm.description"
                  class="row-edit-field"
                  type="text"
                  aria-label="Category description"
                />
              </td>
              <td><span class="order-total">{{ productCount(category.id) }}</span></td>
              <td>
                <div class="order-actions">
                  <button
                    type="button"
                    class="sort-button"
                    :disabled="busy"
                    @click="saveEdit(category)"
                  >
                    Save
                  </button>
                  <button type="button" class="sort-button" @click="cancelEdit">Cancel</button>
                </div>
              </td>
            </template>
            <template v-else>
              <td><strong>{{ category.name }}</strong></td>
              <td><span class="order-date">{{ category.description ?? "—" }}</span></td>
              <td><span class="order-total">{{ productCount(category.id) }}</span></td>
              <td>
                <div class="order-actions">
                  <button type="button" class="sort-button" @click="startEdit(category)">
                    Edit
                  </button>
                  <button
                    type="button"
                    class="row-action row-delete"
                    :aria-label="`Delete ${category.name}`"
                    @click="deleteCategory(category)"
                  >
                    <Icon name="close" :size="14" />
                  </button>
                </div>
              </td>
            </template>
          </tr>
        </tbody>
      </table>
      <p v-if="loading" class="empty-state">Loading categories...</p>
      <p v-else-if="loadError" class="empty-state">{{ loadError }}</p>
    </div>
  </section>
</template>
