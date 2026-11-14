<script setup lang="ts">
import { onMounted, ref } from "vue";

import Icon from "@/components/Icon.vue";
import { ApiError, api } from "@/lib/api";
import { FollowedSchema, type Product } from "@/lib/schemas";
import { useFollows } from "@/stores/follows";
import { useToast } from "@/stores/toast";

// Following 頁（收藏清單）：看收藏商品、取消收藏、點入商品頁。
// 資料來源 GET /products/followed（items 完整商品、收藏時間新 → 舊）。

const { load: loadFollows, toggle: toggleFollowStore } = useFollows();
const toast = useToast();

const items = ref<Product[]>([]);
const loading = ref(true);
const loadError = ref("");
// 圖片載入失敗的 product id：改用空佔位（與店面 brokenImages 同概念）。
const brokenImages = ref<Record<number, boolean>>({});
const busy = ref(false);

function formatPrice(price: string | number): string {
  return `$${Number(price).toFixed(2)}`;
}

async function load(): Promise<void> {
  loading.value = true;
  loadError.value = "";
  try {
    await loadFollows(); // 星星狀態（兩個來源之一，主要是為了 isFollowed 同步）
    const data = await api.get("/products/followed", FollowedSchema);
    items.value = data.items;
  } catch (err) {
    loadError.value =
      err instanceof ApiError ? `Failed to load: ${err.message}` : "Failed to load followed products.";
  } finally {
    loading.value = false;
  }
}

async function unfollow(product: Product): Promise<void> {
  busy.value = true;
  try {
    await toggleFollowStore(product.id);
    items.value = items.value.filter((p) => p.id !== product.id);
    toast.show(`Unfollowed "${product.name}".`);
  } catch (err) {
    toast.show(err instanceof ApiError ? `Unfollow failed: ${err.message}` : "Unfollow failed.");
  } finally {
    busy.value = false;
  }
}

onMounted(load);
</script>

<template>
  <section class="page-heading">
    <div class="th-main">
      <h1>Following</h1>
      <p>Products you follow — we'll notify you when out-of-stock items are back.</p>
    </div>
    <div class="th-cell"><small>Sheet</small><b>FOLLOW-01</b></div>
  </section>

  <section class="data-panel">
    <div class="panel-header">
      <div>
        <h2>Followed products</h2>
        <p v-if="!loading && !loadError">{{ items.length }} products.</p>
      </div>
    </div>

    <p v-if="loading" class="empty-state">Loading followed products...</p>
    <p v-else-if="loadError" class="empty-state">{{ loadError }}</p>
    <p v-else-if="items.length === 0" class="empty-state">
      No followed products yet.
      <router-link :to="{ name: 'storefront' }" class="text-button">Browse the store →</router-link>
    </p>

    <ul v-else class="followed-list">
      <li v-for="product in items" :key="product.id" class="followed-row">
        <router-link
          class="followed-link"
          :to="{ name: 'product-detail', params: { id: product.id } }"
          :aria-label="`Open ${product.name}`"
        >
          <img
            v-if="product.image_url && !brokenImages[product.id]"
            :src="product.image_url"
            :alt="product.name"
            class="followed-thumb"
            @error="brokenImages[product.id] = true"
          />
          <span v-else class="followed-thumb followed-thumb-empty" aria-hidden="true"></span>
          <span class="followed-name">
            <strong>{{ product.name }}</strong>
            <small>{{ product.description ?? "" }}</small>
          </span>
          <span class="followed-price">{{ formatPrice(product.price) }}</span>
          <span
            :class="['stock-badge', product.stock > 0 ? 'in' : 'out']"
          >
            {{ product.stock > 0 ? `In stock · ${product.stock}` : "Out of stock" }}
          </span>
        </router-link>
        <button
          type="button"
          class="row-action row-delete"
          :aria-label="`Unfollow ${product.name}`"
          :disabled="busy"
          @click="unfollow(product)"
        >
          <Icon name="close" :size="14" />
        </button>
      </li>
    </ul>
  </section>
</template>

<!-- followed-* 樣式共用於 FollowingView / CartView → design.css -->
