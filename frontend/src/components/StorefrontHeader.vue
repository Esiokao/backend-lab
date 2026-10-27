<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute } from "vue-router";

import Icon from "@/components/Icon.vue";
import NotificationCenter from "@/components/NotificationCenter.vue";
import { useAuth } from "@/stores/auth";
import { useCart } from "@/stores/cart";
import { usePopover } from "@/stores/popover";
import { useTheme } from "@/stores/theme";

// 店面式頁面的共用 header（Storefront / Cart / Checkout / Result）：
// 品牌 ｜ 分類導覽（deep-link ?cat=） ｜ 右側：主題切換、通知、cart、My account 下拉。
// Sign out 收在 My account 下拉裡（會員）。

const route = useRoute();
const { user, logout } = useAuth();
const { theme, toggleTheme } = useTheme();
const { count: cartCount } = useCart();
const { active: activePopover, openPopover, closePopover } = usePopover();

const isAdmin = () => user.value?.role === "admin";

const initials = computed(() =>
  (user.value?.name ?? "?")
    .split(" ")
    .map((part) => part[0])
    .join("")
    .toUpperCase(),
);

// ── My account 下拉：點按鈕開、點外部/Esc/切頁收 ──
const menuOpen = ref(false);

function onDocumentClick(event: MouseEvent): void {
  const inside = event.target instanceof Element && !!event.target.closest(".sf-account-wrap");
  if (menuOpen.value && !inside) menuOpen.value = false;
}

function onKeydown(event: KeyboardEvent): void {
  if (event.key === "Escape" && menuOpen.value) menuOpen.value = false;
}

onMounted(() => {
  document.addEventListener("click", onDocumentClick);
  document.addEventListener("keydown", onKeydown);
});

onUnmounted(() => {
  document.removeEventListener("click", onDocumentClick);
  document.removeEventListener("keydown", onKeydown);
});

watch(
  () => route.fullPath,
  () => {
    menuOpen.value = false;
  },
);

// 互斥：選單開 → 登記；別的浮層（如通知面板）開 → 收選單。
watch(menuOpen, (open) => {
  if (open) openPopover("account-menu");
  else closePopover("account-menu");
});
watch(activePopover, (name) => {
  if (name !== null && name !== "account-menu" && menuOpen.value) {
    menuOpen.value = false;
  }
});

async function handleLogout(): Promise<void> {
  menuOpen.value = false;
  await logout();
}
</script>

<template>
  <header class="storefront-header">
    <router-link class="brand" :to="{ name: 'storefront' }" aria-label="Back to storefront">
      <span class="brand-mark"><Icon name="bolt" :size="16" /></span>
      <span>Backend Lab</span>
    </router-link>

    <!-- 導覽：All products ＋ About us（手機隱藏） -->
    <nav class="sf-nav" aria-label="Catalog shortcuts">
      <router-link :to="{ name: 'storefront' }">All products</router-link>
      <router-link :to="{ name: 'about' }">About us</router-link>
    </nav>

    <div class="storefront-actions">
      <button
        type="button"
        class="ghost-button theme-switch"
        :aria-label="theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'"
        @click="toggleTheme"
      >
        <Icon :name="theme === 'dark' ? 'sun' : 'moon'" :size="16" />
        <span class="theme-switch-label">{{ theme === "dark" ? "Light" : "Dark" }}</span>
      </button>
      <router-link class="ghost-button theme-toggle cart-link-header" :to="{ name: 'cart' }" aria-label="Cart">
        <Icon name="cart" :size="15" />
        <span v-if="cartCount() > 0" class="cart-count-badge">
          {{ cartCount() > 99 ? "99+" : cartCount() }}
        </span>
      </router-link>
      <!-- 通知鈴鐺：登入者限定（訪客無通知可看） -->
      <NotificationCenter v-if="user" />

      <!-- My account 下拉（會員）：Sign out 在這裡 -->
      <div v-if="user" class="sf-account-wrap">
        <button
          type="button"
          class="sf-account-btn"
          aria-label="Account menu"
          :aria-expanded="menuOpen"
          @click="menuOpen = !menuOpen"
        >
          <span class="avatar">{{ initials }}</span>
          <span class="sf-account-name">{{ user.name }}</span>
          <Icon name="chevron" :size="12" />
        </button>
        <div v-if="menuOpen" class="user-menu" role="menu" aria-label="Account menu">
          <div class="user-menu-header">
            <strong>Hi, {{ user.name }}!</strong>
            <small>{{ user.email }}</small>
          </div>
          <router-link
            class="user-menu-item"
            role="menuitem"
            :to="{ name: isAdmin() ? 'dashboard' : 'account' }"
            @click="menuOpen = false"
          >
            <Icon :name="isAdmin() ? 'grid' : 'users'" :size="14" />
            {{ isAdmin() ? "Workspace" : "My account" }}
          </router-link>
          <router-link
            class="user-menu-item"
            role="menuitem"
            :to="{ name: 'orders' }"
            @click="menuOpen = false"
          >
            <Icon name="box" :size="14" /> My orders
          </router-link>
          <router-link
            class="user-menu-item"
            role="menuitem"
            :to="{ name: 'account-edit' }"
            @click="menuOpen = false"
          >
            <Icon name="users" :size="14" /> Account settings
          </router-link>
          <router-link
            class="user-menu-item"
            role="menuitem"
            :to="{ name: 'account-edit', query: { section: 'password' } }"
            @click="menuOpen = false"
          >
            <Icon name="shield" :size="14" /> Change password
          </router-link>
          <template v-if="isAdmin()">
            <p class="user-menu-label">Administration</p>
            <router-link
              class="user-menu-item"
              role="menuitem"
              :to="{ name: 'admin-orders' }"
              @click="menuOpen = false"
            >
              <Icon name="box" :size="14" /> Order Management
            </router-link>
            <router-link
              class="user-menu-item"
              role="menuitem"
              :to="{ name: 'admin-users' }"
              @click="menuOpen = false"
            >
              <Icon name="users" :size="14" /> User Management
            </router-link>
            <router-link
              class="user-menu-item"
              role="menuitem"
              :to="{ name: 'admin-categories' }"
              @click="menuOpen = false"
            >
              <Icon name="grid" :size="14" /> Category Management
            </router-link>
            <router-link
              class="user-menu-item"
              role="menuitem"
              :to="{ name: 'admin-notifications' }"
              @click="menuOpen = false"
            >
              <Icon name="bell" :size="14" /> Notifications
            </router-link>
          </template>
          <button
            type="button"
            class="user-menu-item user-menu-signout"
            role="menuitem"
            @click="handleLogout"
          >
            <Icon name="logout" :size="14" /> Sign out
          </button>
        </div>
      </div>
      <router-link v-else class="primary-button" :to="{ name: 'login' }">
        Sign in
      </router-link>
    </div>
  </header>
</template>
