<script setup lang="ts">
import Icon from "@/components/Icon.vue";
import { useAuth } from "@/stores/auth";
import { useCart } from "@/stores/cart";
import { useTheme } from "@/stores/theme";

// 店面式頁面的共用 header（Storefront / Cart）：品牌、主題切換、
// cart icon（帶數量徽章）、Workspace/My account 與 Sign out（或 Sign in）。

const { user, logout } = useAuth();
const { theme, toggleTheme } = useTheme();
const { count: cartCount } = useCart();

const isAdmin = () => user.value?.role === "admin";

async function handleLogout(): Promise<void> {
  // 登出後留在當前店面頁，header 自動切回訪客狀態。
  await logout();
}
</script>

<template>
  <header class="storefront-header">
    <router-link class="brand" :to="{ name: 'storefront' }" aria-label="Back to storefront">
      <span class="brand-mark"><Icon name="bolt" :size="16" /></span>
      <span>Backend Lab</span>
    </router-link>
    <div class="storefront-actions">
      <button
        type="button"
        class="ghost-button theme-toggle"
        :aria-label="theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'"
        @click="toggleTheme"
      >
        <Icon :name="theme === 'dark' ? 'sun' : 'moon'" :size="15" />
      </button>
      <router-link class="ghost-button theme-toggle cart-link-header" :to="{ name: 'cart' }" aria-label="Cart">
        <Icon name="cart" :size="15" />
        <span v-if="cartCount() > 0" class="cart-count-badge">
          {{ cartCount() > 99 ? "99+" : cartCount() }}
        </span>
      </router-link>
      <template v-if="user">
        <router-link
          class="ghost-button"
          :to="isAdmin() ? { name: 'dashboard' } : { name: 'account' }"
        >
          <Icon :name="isAdmin() ? 'grid' : 'users'" :size="14" />
          {{ isAdmin() ? "Workspace" : "My account" }}
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
</template>
