<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import Icon from "@/components/Icon.vue";
import { api } from "@/lib/api";
import { useAuth } from "@/stores/auth";
import { useToast } from "@/stores/toast";

// 公開店面（v1.4）：訪客可瀏覽 GET /products（後端已公開化）；
// 未登入按關注 → 導向 /login?redirect=（F12-7）。
// 下單流程與 admin 管理控件屬 PR-3，不在本頁。

type Product = {
  id: number;
  name: string;
  description: string | null;
  image_url: string | null;
  price: string | number; // 後端 Decimal 序列化相容字串/數字
  stock: number;
};

const PAGE_SIZE = 12;

const route = useRoute();
const router = useRouter();
const { user, logout } = useAuth();
const { message: toastMessage, show: showToast, dismiss: dismissToast } = useToast();

const products = ref<Product[]>([]);
const loading = ref(true);
const loadError = ref("");
const page = ref(1);
const query = ref("");
const appliedQuery = ref("");

// 後端商品列表無 total 欄位：回滿一頁視為還有下一頁。
const hasMore = computed(() => products.value.length === PAGE_SIZE);

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

async function handleFollow(product: Product): Promise<void> {
  if (!user.value) {
    // 未登入 → 登入頁帶 redirect，登入後回店面（F12-7）。
    await router.push({ name: "login", query: { redirect: route.fullPath } });
    return;
  }

  try {
    // 後端冪等：重複關注不會產生重複資料，仍回 200。
    await api.post(`/products/${product.id}/follow`);
    showToast(`Following "${product.name}" — we'll notify you when it's back in stock.`);
  } catch {
    showToast("Follow failed. Please try again.");
  }
}

async function handleLogout(): Promise<void> {
  // 登出後留在店面，header 自動切回訪客狀態。
  await logout();
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

    <p v-if="loading" class="empty-state">Loading products…</p>
    <p v-else-if="loadError" class="empty-state">{{ loadError }}</p>
    <p v-else-if="products.length === 0" class="empty-state">No products found.</p>

    <section v-else class="product-grid" aria-label="Product catalog">
      <article v-for="product in products" :key="product.id" class="product-card">
        <div class="product-media">
          <img
            v-if="product.image_url"
            :src="product.image_url"
            :alt="product.name"
            loading="lazy"
          />
          <span v-else class="product-media-fallback"><Icon name="box" :size="26" /></span>
        </div>
        <div class="product-body">
          <h2>{{ product.name }}</h2>
          <p v-if="product.description">{{ product.description }}</p>
        </div>
        <div class="product-foot">
          <span class="product-price">{{ formatPrice(product.price) }}</span>
          <span :class="['stock-badge', product.stock > 0 ? 'in' : 'out']">
            {{ product.stock > 0 ? `In stock · ${product.stock}` : "Out of stock" }}
          </span>
          <button
            v-if="user"
            type="button"
            class="follow-button"
            :aria-label="`Follow ${product.name} for restock alerts`"
            @click="handleFollow(product)"
          >
            <Icon name="shield" :size="13" /> Follow
          </button>
          <router-link
            v-else
            class="follow-button"
            :aria-label="`Sign in to follow ${product.name}`"
            :to="{ name: 'login', query: { redirect: route.fullPath } }"
          >
            <Icon name="shield" :size="13" /> Sign in to follow
          </router-link>
        </div>
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
