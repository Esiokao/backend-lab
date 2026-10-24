<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import Icon from "@/components/Icon.vue";
import { useAuth } from "@/stores/auth";
import { useCart } from "@/stores/cart";
import { useTheme } from "@/stores/theme";
import { useNotifications } from "@/stores/notifications";

const route = useRoute();
const router = useRouter();

const { user, logout } = useAuth();
const { theme, setTheme } = useTheme();
const { count: cartCount, refresh: refreshCart } = useCart();
const {
  unreadCount,
  items: notifications,
  broadcasts,
  panelOpen,
  startPolling,
  stopPolling,
  togglePanel,
  markRead,
  markAllRead,
} = useNotifications();

const isAdmin = computed(() => user.value?.role === "admin");

type NavItem = { label: string; icon: "bolt" | "grid" | "box" | "activity" | "users" | "cart"; to: { name: string }; dot?: boolean };

// 依角色分區（v1.5）：workspace（系統監控）僅 admin 可見；
// 一般使用者是會員中心視角（My Orders / Account）。
const navItems = computed<NavItem[]>(() =>
  isAdmin.value
    ? [
        { label: "Storefront", icon: "bolt", to: { name: "storefront" } },
        { label: "Overview", icon: "grid", to: { name: "dashboard" } },
        { label: "Orders", icon: "box", to: { name: "orders" } },
        { label: "API Health", icon: "activity", to: { name: "api-health" }, dot: true },
      ]
    : [
        { label: "Storefront", icon: "bolt", to: { name: "storefront" } },
        { label: "Cart", icon: "cart", to: { name: "cart" } },
        { label: "My Orders", icon: "box", to: { name: "orders" } },
        { label: "Account", icon: "users", to: { name: "account" } },
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
  // Esc 是面板與選單的標準出口（critique：role=dialog 沒有 Esc 是 a11y 債）。
  if (event.key !== "Escape") return;
  if (panelOpen.value) togglePanel();
  if (menuOpen.value) menuOpen.value = false;
}

// 通知輪詢（F11）：登入期間開啟，離開應用區關閉。
onMounted(() => {
  if (user.value) startPolling();
  if (user.value) void refreshCart();
  document.addEventListener("click", onDocumentClick);
  document.addEventListener("keydown", onKeydown);
  void probeBackend();
  probeTimer = window.setInterval(() => void probeBackend(), 30_000);
});

onUnmounted(() => {
  stopPolling();
  document.removeEventListener("click", onDocumentClick);
  document.removeEventListener("keydown", onKeydown);
  if (probeTimer !== undefined) window.clearInterval(probeTimer);
});

// 切換路由時收起通知面板與頭像選單：兩者都是全域狀態，不收會蓋住下一頁內容。
watch(
  () => route.fullPath,
  () => {
    if (panelOpen.value) togglePanel();
    menuOpen.value = false;
  },
);

// 通知面板分頁：一般通知（個人、可標已讀）／廣播（系統公告）。開啟面板時回到一般。
const notifTab = ref<"general" | "broadcast">("general");

watch(panelOpen, (open) => {
  if (open) notifTab.value = "general";
});

watch(user, (value) => {
  if (value) startPolling();
  else stopPolling();
});

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString();
}
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
          <router-link :to="{ name: 'cart' }" class="bell-button cart-link" aria-label="Cart">
            <Icon name="cart" :size="17" />
            <span v-if="cartCount() > 0" class="bell-badge">
              {{ cartCount() > 99 ? "99+" : cartCount() }}
            </span>
          </router-link>
          <div class="bell-wrap">
            <button type="button" class="bell-button" aria-label="Notifications" @click="togglePanel">
              <Icon name="bell" :size="17" />
              <span v-if="unreadCount > 0" class="bell-badge">
                {{ unreadCount > 99 ? "99+" : unreadCount }}
              </span>
            </button>
            <div v-if="panelOpen" class="notif-panel" role="dialog" aria-label="Notifications panel">
              <div class="notif-panel-header">
                <strong>Notifications</strong>
                <div class="notif-panel-actions">
                  <button
                    v-if="notifTab === 'general'"
                    type="button"
                    class="text-button"
                    @click="markAllRead"
                  >
                    Mark all read
                  </button>
                  <button type="button" class="row-action" aria-label="Close notifications" @click="togglePanel">
                    <Icon name="close" :size="14" />
                  </button>
                </div>
              </div>
              <div class="notif-tabs" role="tablist" aria-label="Notification type">
                <button
                  type="button"
                  role="tab"
                  :aria-selected="notifTab === 'general'"
                  :class="['notif-tab', { active: notifTab === 'general' }]"
                  @click="notifTab = 'general'"
                >
                  General
                  <span v-if="unreadCount > 0" class="notif-tab-badge">
                    {{ unreadCount > 99 ? "99+" : unreadCount }}
                  </span>
                </button>
                <button
                  type="button"
                  role="tab"
                  :aria-selected="notifTab === 'broadcast'"
                  :class="['notif-tab', { active: notifTab === 'broadcast' }]"
                  @click="notifTab = 'broadcast'"
                >
                  System
                  <span v-if="broadcasts.length > 0" class="notif-tab-badge">{{ broadcasts.length }}</span>
                </button>
              </div>
              <div class="notif-panel-body">
                <div v-if="notifTab === 'general'">
                  <p v-if="notifications.length === 0" class="notif-empty">
                    No general notifications yet.
                  </p>
                  <ul v-else class="notif-list">
                    <li v-for="notification in notifications" :key="notification.id">
                      <button
                        type="button"
                        :class="['notif-item', { unread: notification.read_at === null }]"
                        @click="markRead(notification)"
                      >
                        <span class="notif-title">
                          <i v-if="notification.read_at === null" class="notif-dot" />{{ notification.title }}
                        </span>
                        <span class="notif-body">{{ notification.body }}</span>
                        <span class="notif-time">{{ formatTime(notification.created_at) }}</span>
                      </button>
                    </li>
                  </ul>
                </div>
                <div v-else>
                  <p v-if="broadcasts.length === 0" class="notif-empty">
                    No system broadcasts yet.
                  </p>
                  <ul v-else class="notif-list">
                    <li v-for="broadcast in broadcasts" :key="broadcast.id">
                      <div class="notif-item broadcast">
                        <span class="notif-title">{{ broadcast.title }}</span>
                        <span class="notif-body">{{ broadcast.body }}</span>
                        <span class="notif-time">{{ formatTime(broadcast.created_at) }}</span>
                      </div>
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
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
                :to="{ name: 'account', query: { section: 'password' } }"
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
