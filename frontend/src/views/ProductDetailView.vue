<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import Icon from "@/components/Icon.vue";
import StorefrontFooter from "@/components/StorefrontFooter.vue";
import StorefrontHeader from "@/components/StorefrontHeader.vue";
import { ApiError, api } from "@/lib/api";
import {
  CategoryPageSchema,
  ProductSchema,
  type Category,
  type Product,
} from "@/lib/schemas";
import { useAuth } from "@/stores/auth";
import { useCart } from "@/stores/cart";
import { useToast } from "@/stores/toast";

// 商品詳情頁（v1.18）：修 P0「商品卡是死路」——公開 GET /products/{id}，
// 大圖 + 完整名稱/描述 + 價格/庫存 + 加購/關注；店面卡片圖片與名稱連入。

const route = useRoute();
const router = useRouter();
const { user } = useAuth();
const { add: addToCart } = useCart();
const { show: showToast } = useToast();

const product = ref<Product | null>(null);
const loading = ref(true);
const loadError = ref("");
const brokenImage = ref(false);

// Follow 為 session 內樂觀 UI（與店面同語彙）：後端尚無「查詢我是否已關注」端點。
const followed = ref(false);

const categories = ref<Category[]>([]);
const categoryName = computed(() => {
  if (product.value === null || product.value.category_id === null) return "Uncategorized";
  return categories.value.find((c) => c.id === product.value?.category_id)?.name ?? "Uncategorized";
});

// NEW IN（與店面同規則：created_at 7 天內）。
const isNew = computed(() => {
  if (product.value === null) return false;
  const created = new Date(product.value.created_at).getTime();
  return Date.now() - created < 7 * 24 * 60 * 60 * 1000;
});

function formatPrice(price: string | number): string {
  return `$${Number(price).toFixed(2)}`;
}

async function toggleFollow(): Promise<void> {
  if (product.value === null) return;
  if (!user.value) {
    await router.push({ name: "login", query: { redirect: route.fullPath } });
    return;
  }
  try {
    if (followed.value) {
      await api.delete(`/products/${product.value.id}/follow`);
      followed.value = false;
      showToast(`Unfollowed "${product.value.name}".`);
    } else {
      await api.post(`/products/${product.value.id}/follow`);
      followed.value = true;
      showToast(
        product.value.stock > 0
          ? `Following "${product.value.name}".`
          : `Following "${product.value.name}" — we'll notify you when it's back in stock.`,
      );
    }
  } catch {
    showToast("Follow failed. Please try again.");
  }
}

async function handleAddToCart(): Promise<void> {
  if (product.value === null) return;
  if (!user.value) {
    await router.push({ name: "login", query: { redirect: route.fullPath } });
    return;
  }
  if (product.value.stock <= 0) {
    showToast(`"${product.value.name}" is out of stock.`);
    return;
  }
  try {
    await addToCart(product.value.id, 1);
    showToast(`Added "${product.value.name}" to cart.`);
  } catch (err) {
    showToast(
      err instanceof ApiError ? `Add to cart failed: ${err.message}` : "Add to cart failed.",
    );
  }
}

onMounted(async () => {
  const id = Number(route.params.id);
  if (!Number.isInteger(id) || id <= 0) {
    loadError.value = "Product not found.";
    loading.value = false;
    return;
  }
  try {
    const [fetched, cats] = await Promise.all([
      api.get(`/products/${id}`, ProductSchema),
      api
        .get("/categories", CategoryPageSchema)
        .then((page) => page.items)
        .catch(() => [] as Category[]),
    ]);
    product.value = fetched;
    categories.value = cats;
    document.title = `${fetched.name} · Backend Lab`;
  } catch (err) {
    loadError.value =
      err instanceof ApiError && err.status === 404
        ? "Product not found."
        : "Failed to load product.";
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <StorefrontHeader />

  <main class="storefront-main">
    <section class="page-heading">
      <div class="th-main">
        <h1>{{ product?.name ?? "Product" }}</h1>
        <p>Item detail — full name, description and stock before you commit.</p>
      </div>
      <router-link :to="{ name: 'storefront' }" class="text-button">
        <Icon name="arrow" :size="15" /> Back to storefront
      </router-link>
      <div class="th-cell">
        <small>Sheet</small>
        <b>{{ product === null ? "PROD-—" : `PROD-${String(product.id).padStart(2, "0")}` }}</b>
      </div>
    </section>

    <p v-if="loading" class="empty-state">Loading product…</p>
    <p v-else-if="loadError" class="empty-state">{{ loadError }}</p>

    <div v-else-if="product" class="product-detail-layout">
      <div class="pd-media">
        <img
          v-if="product.image_url && !brokenImage"
          :src="product.image_url"
          :alt="product.name"
          @error="brokenImage = true"
        />
        <span v-else class="pd-media-fallback"><Icon name="box" :size="40" /></span>
        <button
          v-if="user"
          type="button"
          :class="['follow-star', { active: followed }]"
          :aria-label="followed ? `Unfollow ${product.name}` : `Follow ${product.name}`"
          :aria-pressed="followed"
          @click="toggleFollow"
        >
          <Icon name="star" :size="15" />
        </button>
        <button
          v-else
          type="button"
          class="follow-star"
          :aria-label="`Sign in to follow ${product.name}`"
          @click="toggleFollow"
        >
          <Icon name="star" :size="15" />
        </button>
      </div>

      <div class="pd-info">
        <div class="pd-tags">
          <span class="tag-stamp cat">{{ categoryName }}</span>
          <span v-if="isNew" class="tag-stamp new">New in</span>
        </div>
        <h2 class="pd-name">{{ product.name }}</h2>
        <span class="pd-price">{{ formatPrice(product.price) }}</span>
        <p class="pd-desc">{{ product.description ?? "No description provided for this item." }}</p>

        <div class="pd-actions">
          <button
            v-if="product.stock > 0"
            type="button"
            class="ghost-button product-add-button"
            @click="handleAddToCart"
          >
            <Icon name="cart" :size="15" /> Add to cart
          </button>
          <button
            v-else-if="followed"
            type="button"
            class="ghost-button product-add-button following"
            disabled
          >
            <Icon name="star" :size="15" /> Following — restock alert on
          </button>
          <button
            v-else
            type="button"
            class="ghost-button product-add-button notify"
            @click="toggleFollow"
          >
            <Icon name="star" :size="15" /> Out of stock — notify me
          </button>
        </div>

        <div class="pd-panel">
          <div class="pd-meta-row">
            <small>Availability</small>
            <span :class="['stock-badge', product.stock > 0 ? 'in' : 'out']">
              {{ product.stock > 0 ? `In stock · ${product.stock}` : "Out of stock" }}
            </span>
          </div>
          <div class="pd-meta-row">
            <small>Sheet ref</small>
            <strong class="order-total">PROD-{{ String(product.id).padStart(2, "0") }}</strong>
          </div>
          <div class="pd-meta-row">
            <small>Added</small>
            <strong>{{ new Date(product.created_at).toLocaleDateString() }}</strong>
          </div>
        </div>
      </div>
    </div>
  </main>

  <StorefrontFooter />
</template>
