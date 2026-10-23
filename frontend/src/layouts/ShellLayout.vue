<script setup lang="ts">
import { computed, onMounted, onUnmounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import Icon from "@/components/Icon.vue";
import { useAuth } from "@/stores/auth";
import { useNotifications } from "@/stores/notifications";
import { useToast } from "@/stores/toast";

const route = useRoute();
const router = useRouter();

const { user, logout } = useAuth();
const { message, dismiss } = useToast();
const {
  unreadCount,
  items: notifications,
  panelOpen,
  startPolling,
  stopPolling,
  togglePanel,
  markRead,
  markAllRead,
} = useNotifications();

const navItems = [
  { label: "Overview", icon: "grid", to: { name: "dashboard" } },
  { label: "Orders", icon: "box", to: { name: "orders" } },
  { label: "API Health", icon: "activity", to: { name: "api-health" }, dot: true },
] as const;

// Administration 分區：僅 admin 可見（F10-1）。
const adminNavItems = [
  { label: "Order Management", icon: "box", to: { name: "admin-orders" } },
  { label: "User Management", icon: "users", to: { name: "admin-users" } },
] as const;

const isAdmin = computed(() => user.value?.role === "admin");

const currentLabel = computed(() => {
  const items = isAdmin.value ? [...navItems, ...adminNavItems] : [...navItems];
  const match = items.find((item) => item.to.name === route.name);
  return match?.label ?? "Overview";
});

const initials = computed(() =>
  (user.value?.name ?? "?")
    .split(" ")
    .map((part) => part[0])
    .join("")
    .toUpperCase(),
);

async function handleLogout(): Promise<void> {
  await logout();
  await router.push({ name: "login" });
}

// 通知輪詢（F11）：登入期間開啟，離開應用區關閉。
onMounted(() => {
  if (user.value) startPolling();
});

onUnmounted(stopPolling);

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
        <div class="brand">
          <span class="brand-mark"><Icon name="bolt" :size="16" /></span>
          <span>Backend Lab</span>
        </div>
        <nav class="side-nav" aria-label="Main navigation">
          <p class="nav-label">Workspace</p>
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
        <div class="environment-card">
          <div class="environment-heading">
            <Icon name="server" :size="16" /><span>Environment</span>
          </div>
          <button type="button" class="environment-select">
            <span><i /> Production</span><Icon name="chevron" :size="14" />
          </button>
        </div>
        <button type="button" class="profile" @click="handleLogout">
          <span class="avatar">{{ initials }}</span>
          <span class="profile-copy">
            <strong>{{ user?.name ?? "Loading..." }}</strong>
            <small>{{ user?.email ?? "" }}</small>
          </span>
          <Icon name="logout" :size="17" />
        </button>
      </div>
    </aside>

    <main class="main-content">
      <header class="topbar">
        <div class="mobile-brand">
          <span class="brand-mark"><Icon name="bolt" :size="15" /></span
          ><strong>Backend Lab</strong>
        </div>
        <div class="breadcrumb">
          <span>Backend Lab</span><Icon name="arrow" :size="14" /><strong>{{
            currentLabel
          }}</strong>
        </div>
        <div class="topbar-actions">
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
                  <button type="button" class="text-button" @click="markAllRead">Mark all read</button>
                  <button type="button" class="row-action" aria-label="Close notifications" @click="togglePanel">
                    <Icon name="close" :size="14" />
                  </button>
                </div>
              </div>
              <p v-if="notifications.length === 0" class="notif-empty">No notifications yet.</p>
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
          </div>
          <span class="live-pill"><i /> All systems operational</span>
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

    <Transition name="toast">
      <div v-if="message" class="toast" role="status">
        <span><Icon name="shield" :size="17" /></span>{{ message }}
        <button type="button" aria-label="Dismiss notification" @click="dismiss">
          <Icon name="close" :size="15" />
        </button>
      </div>
    </Transition>
  </div>
</template>
