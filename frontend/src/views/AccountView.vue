<script setup lang="ts">
import { computed } from "vue";

import Icon from "@/components/Icon.vue";
import { useAuth } from "@/stores/auth";

// 會員中心（/app/account）：唯讀顯示目前使用者資料；
// 要變更 → /app/account/edit（資料修改 + 改密碼）。

const { user } = useAuth();

const initials = computed(() =>
  (user.value?.name ?? "?")
    .split(" ")
    .map((part) => part[0])
    .join("")
    .toUpperCase(),
);
</script>

<template>
  <section class="page-heading">
    <div class="th-main">
      <h1>My account</h1>
      <p>Your membership information.</p>
    </div>
    <router-link :to="{ name: 'account-edit' }" class="primary-button">
      <Icon name="arrow" :size="15" /> Edit profile
    </router-link>
    <div class="th-cell"><small>Sheet</small><b>ACCOUNT-01</b></div>
  </section>

  <section class="data-panel user-detail-card" aria-label="Member info">
    <div class="user-cell">
      <span class="mini-avatar">{{ initials }}</span>
      <span>
        <strong>{{ user?.name }}</strong>
        <small>{{ user?.email }}</small>
      </span>
    </div>
    <div class="user-detail-meta">
      <span class="role-badge" :class="user?.role">{{ user?.role }}</span>
      <code>usr_{{ String(user?.id ?? "").padStart(4, "0") }}</code>
    </div>
  </section>

  <section class="data-panel" aria-label="Account details">
    <div class="panel-header">
      <div>
        <h2>Details</h2>
        <p>Changes are made in the edit section.</p>
      </div>
    </div>
    <div class="info-rows">
      <div class="info-row">
        <small>Name</small>
        <strong>{{ user?.name }}</strong>
      </div>
      <div class="info-row">
        <small>Email</small>
        <strong>{{ user?.email }}</strong>
      </div>
      <div class="info-row">
        <small>Role</small>
        <strong>{{ user?.role }}</strong>
      </div>
      <div class="info-row">
        <small>User ID</small>
        <strong class="mono-value">usr_{{ String(user?.id ?? "").padStart(4, "0") }}</strong>
      </div>
    </div>
  </section>
</template>
