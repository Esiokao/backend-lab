<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";

import Icon from "@/components/Icon.vue";
import { useAuth } from "@/stores/auth";
import { useToast } from "@/stores/toast";

const route = useRoute();
const router = useRouter();

const { user, logout } = useAuth();
const { message, dismiss } = useToast();

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
