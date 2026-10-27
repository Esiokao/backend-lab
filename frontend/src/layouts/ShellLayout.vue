<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import Icon from "@/components/Icon.vue";
import NotificationCenter from "@/components/NotificationCenter.vue";
import { useAuth } from "@/stores/auth";
import { useCart } from "@/stores/cart";
import { usePopover } from "@/stores/popover";
import { useTheme } from "@/stores/theme";

const route = useRoute();
const router = useRouter();

const { user, logout } = useAuth();
const { theme, setTheme, toggleTheme } = useTheme();
const { count: cartCount, refresh: refreshCart } = useCart();
const { active: activePopover, openPopover, closePopover } = usePopover();
const isAdmin = computed(() => user.value?.role === "admin");

type NavItem = { label: string; icon: "bolt" | "grid" | "box" | "activity" | "users" | "cart" | "pencil"; to: { name: string }; dot?: boolean };

// 依角色分區（v1.5）：workspace（系統監控）僅 admin 可見；
// 一般使用者是會員中心視角（My Orders / Account）。
const navItems = computed<NavItem[]>(() =>
  isAdmin.value
    ? [
        { label: "Store", icon: "bolt", to: { name: "storefront" } },
        { label: "Overview", icon: "grid", to: { name: "dashboard" } },
        { label: "Orders", icon: "box", to: { name: "orders" } },
        { label: "API Health", icon: "activity", to: { name: "api-health" }, dot: true },
      ]
    : [
        { label: "Store", icon: "bolt", to: { name: "storefront" } },
        { label: "My Orders", icon: "box", to: { name: "orders" } },
        { label: "Account", icon: "users", to: { name: "account" } },
        { label: "Edit Profile", icon: "pencil", to: { name: "account-edit" } },
      ],
);

// Administration 分區：僅 admin 可見（F10-1）。
const adminNavItems = [
  { label: "Order Management", icon: "box", to: { name: "admin-orders" } },
  { label: "User Management", icon: "users", to: { name: "admin-users" } },
  { label: "Category Management", icon: "grid", to: { name: "admin-categories" } },
  { label: "Notifications", icon: "bell", to: { name: "admin-notifications" } },
] as const;

const currentLabel = computed(() => {
  const items = isAdmin.value ? [...navItems.value, ...adminNavItems] : [...navItems.value];
  const match = items.find((item) => item.to.name === route.name);
  return match?.label ?? (isAdmin.value ? "Overview" : "My Orders");
});

const initials = computed(() =>
  (user.value?.name ?? "?")
    .split(" ")
    .map((part) => part[0])
    .join("")
    .toUpperCase(),
);

async function handleLogout(): Promise<void> {
  // 登出是下拉選單中的明確動作，仍保留一層確認避免誤觸。
  if (!window.confirm("Sign out of Backend Lab?")) return;
  menuOpen.value = false;
  await logout();
  await router.push({ name: "login" });
}

// 頭像下拉選單（會員資料 list）：點頭像展開、點外部或切頁收起。
const menuOpen = ref(false);

function onDocumentClick(event: MouseEvent): void {
  const insideMenu = event.target instanceof Element && !!event.target.closest(".user-menu-wrap");
  if (menuOpen.value && !insideMenu) menuOpen.value = false;
}

// live-pill 接真資料：輕量 /ready 探測（30s 一次），不再寫死「operational」。
const backendUp = ref(true);
const backendCheckedAt = ref("");
const backendTitle = computed(() =>
  backendCheckedAt.value ? `checked ${backendCheckedAt.value}` : "",
);
let probeTimer: number | undefined;

async function probeBackend(): Promise<void> {
  try {
    const response = await fetch("/api/ready", { credentials: "include" });
    backendUp.value = response.ok;
  } catch {
    backendUp.value = false;
  }
  backendCheckedAt.value = new Date().toLocaleTimeString();
}

function onKeydown(event: KeyboardEvent): void {
  // Esc 是頭像選單的標準出口（通知面板的 Esc 由 NotificationCenter 自理）。
  if (event.key === "Escape" && menuOpen.value) menuOpen.value = false;
}

// 通知輪詢（F11）：登入期間開啟，離開應用區關閉。
// cart 徽章跟著登入狀態刷新（通知輪詢由 NotificationCenter 擁有）。
onMounted(() => {
  if (user.value) void refreshCart();
  document.addEventListener("click", onDocumentClick);
  document.addEventListener("keydown", onKeydown);
  void probeBackend();
  probeTimer = window.setInterval(() => void probeBackend(), 30_000);
});

onUnmounted(() => {
  document.removeEventListener("click", onDocumentClick);
  document.removeEventListener("keydown", onKeydown);
  if (probeTimer !== undefined) window.clearInterval(probeTimer);
});

// 切換路由時收起頭像選單（通知面板由 NotificationCenter 卸載時收）。
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
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div>
        <router-link :to="{ name: 'storefront' }" class="brand" aria-label="Back to storefront">
          <span class="brand-mark"><Icon name="bolt" :size="16" /></span>
          <span>Backend Lab</span>
        </router-link>
        <nav class="side-nav" aria-label="Main navigation">
          <p class="nav-label">{{ isAdmin ? "Workspace" : "Member" }}</p>
          <router-link
            v-for="item in navItems"
            :key="item.label"
            :to="item.to"
            :class="['nav-item', { active: currentLabel === item.label }]"
          >
            <Icon :name="item.icon" />
            <span>{{ item.label }}</span>
            <span v-if="'dot' in item && item.dot" class="status-dot" />
          </router-link>
        </nav>
        <nav v-if="isAdmin" class="side-nav" aria-label="Administration navigation">
          <p class="nav-label">Administration</p>
          <router-link
            v-for="item in adminNavItems"
            :key="item.label"
            :to="item.to"
            :class="['nav-item', { active: currentLabel === item.label }]"
          >
            <Icon :name="item.icon" />
            <span>{{ item.label }}</span>
          </router-link>
        </nav>
      </div>

      <div class="sidebar-bottom">
        <!-- 會員身分卡：資訊顯示；互動（會員選單）在右上角頭像。 -->
        <div class="profile">
          <span class="avatar">{{ initials }}</span>
          <span class="profile-copy">
            <strong>{{ user?.name ?? "Loading..." }}</strong>
            <small>{{ user?.email ?? "" }}</small>
          </span>
          <small class="rev-mark" title="Drawing revision">REV A</small>
        </div>
      </div>
    </aside>

    <main class="main-content">
      <header class="topbar">
        <div class="mobile-brand">
          <span class="brand-mark"><Icon name="bolt" :size="15" /></span
          ><strong>Backend Lab</strong>
        </div>
        <div class="breadcrumb">
          <router-link :to="{ name: 'storefront' }" class="breadcrumb-home">Backend Lab</router-link>
          <Icon name="arrow" :size="14" /><strong>{{ currentLabel }}</strong>
        </div>
        <div class="topbar-actions">
          <button
            type="button"
            class="ghost-button theme-switch"
            :aria-label="theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'"
            @click="toggleTheme"
          >
            <Icon :name="theme === 'dark' ? 'sun' : 'moon'" :size="16" />
            <span class="theme-switch-label">{{ theme === "dark" ? "Light" : "Dark" }}</span>
          </button>
          <router-link :to="{ name: 'cart' }" class="bell-button cart-link" aria-label="Cart">
            <Icon name="cart" :size="17" />
            <span v-if="cartCount() > 0" class="bell-badge">
              {{ cartCount() > 99 ? "99+" : cartCount() }}
            </span>
          </router-link>
          <NotificationCenter />

          <span class="live-pill" :class="{ down: !backendUp }" :title="backendTitle">
            <i /> {{ backendUp ? "All systems operational" : "Systems degraded" }}
          </span>
          <div class="user-menu-wrap">
            <button
              type="button"
              class="topbar-avatar"
              aria-label="Account menu"
              :aria-expanded="menuOpen"
              @click="menuOpen = !menuOpen"
            >
              <span class="avatar">{{ initials }}</span>
              <span class="topbar-avatar-name">{{ user?.name }}</span>
              <Icon name="chevron" :size="12" />
            </button>
            <div v-if="menuOpen" class="user-menu" role="menu" aria-label="Account menu">
              <div class="user-menu-header">
                <strong>Hi, {{ user?.name }}!</strong>
                <small>{{ user?.email }}</small>
              </div>
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
                :to="{ name: 'account' }"
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
              <p class="user-menu-label">Appearance</p>
              <button
                type="button"
                :class="['user-menu-item', { current: theme === 'light' }]"
                role="menuitemradio"
                :aria-checked="theme === 'light'"
                @click="setTheme('light')"
              >
                <Icon name="sun" :size="14" /> Light
              </button>
              <button
                type="button"
                :class="['user-menu-item', { current: theme === 'dark' }]"
                role="menuitemradio"
                :aria-checked="theme === 'dark'"
                @click="setTheme('dark')"
              >
                <Icon name="moon" :size="14" /> Dark
              </button>
              <template v-if="isAdmin">
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
        </div>
      </header>

      <div class="mobile-nav">
        <router-link
          v-for="item in navItems"
          :key="item.label"
          :to="item.to"
          :class="{ active: currentLabel === item.label }"
          >{{ item.label }}</router-link
        >
        <template v-if="isAdmin">
          <router-link
            v-for="item in adminNavItems"
            :key="item.label"
            :to="item.to"
            :class="{ active: currentLabel === item.label }"
            >{{ item.label }}</router-link
          >
        </template>
      </div>

      <div class="content-wrap">
        <router-view />
      </div>
    </main>

  </div>
</template>
