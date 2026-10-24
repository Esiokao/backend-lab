<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import Icon from "@/components/Icon.vue";
import { ApiError, api } from "@/lib/api";
import { useAuth } from "@/stores/auth";
import { useToast } from "@/stores/toast";

// 會員中心（/app/account）：
// - 會員資料卡 + 會員資料修改（PATCH /users/{id}，本人）
// - 修改密碼（PATCH /users/{id} 帶 password → 後端撤銷全部 session，含本機）：
//   成功後強制重新登入。
// - ?section=password 直接聚焦修改密碼（下拉選單的 Change password 入口）。

const route = useRoute();
const router = useRouter();
const toast = useToast();
const { user, setUser, logout } = useAuth();

const initials = computed(() =>
  (user.value?.name ?? "?")
    .split(" ")
    .map((part) => part[0])
    .join("")
    .toUpperCase(),
);

// ── 會員資料修改 ──
const profileForm = ref({ name: "", email: "" });
const profileBusy = ref(false);
const profileDirty = computed(
  () =>
    profileForm.value.name !== (user.value?.name ?? "") ||
    profileForm.value.email !== (user.value?.email ?? ""),
);

async function saveProfile(): Promise<void> {
  if (!user.value) return;

  const name = profileForm.value.name.trim();
  const email = profileForm.value.email.trim();

  if (!name || !email) {
    toast.show("Name and email are required.");
    return;
  }

  profileBusy.value = true;
  try {
    const updated = await api.patch<{ id: number; name: string; email: string; role: "user" | "admin" }>(
      `/users/${user.value.id}`,
      { name, email },
    );
    setUser({ ...user.value, name: updated.name, email: updated.email });
    toast.show("Profile updated.");
  } catch (err) {
    toast.show(
      err instanceof ApiError
        ? err.status === 409
          ? "That email is already taken."
          : `Update failed: ${err.message}`
        : "Update failed.",
    );
  } finally {
    profileBusy.value = false;
  }
}

// ── 修改密碼 ──
const passwordForm = ref({ next: "", confirm: "" });
const passwordBusy = ref(false);
const passwordSection = ref<HTMLElement | null>(null);

async function changePassword(): Promise<void> {
  if (!user.value) return;

  const { next, confirm } = passwordForm.value;

  // PRD F7：密碼 8–128 字元。
  if (next.length < 8 || next.length > 128) {
    toast.show("Password must be 8–128 characters.");
    return;
  }
  if (next !== confirm) {
    toast.show("Passwords do not match.");
    return;
  }

  passwordBusy.value = true;
  try {
    await api.patch(`/users/${user.value.id}`, { password: next });
    // 後端已撤銷全部 session（含本機）——強制回登入頁。
    // ?changed=1 讓登入頁顯示持久橫幅：toast 會被轉場吃掉（critique P0）。
    toast.show("Password changed. Please sign in again.");
    await logout();
    await router.push({ name: "login", query: { changed: "1" } });
  } catch (err) {
    toast.show(
      err instanceof ApiError ? `Change failed: ${err.message}` : "Change failed.",
    );
  } finally {
    passwordBusy.value = false;
  }
}

onMounted(() => {
  profileForm.value.name = user.value?.name ?? "";
  profileForm.value.email = user.value?.email ?? "";

  // 下拉選單的 Change password 入口：/app/account?section=password
  if (route.query.section === "password") {
    passwordSection.value?.scrollIntoView({ behavior: "smooth", block: "start" });
  }
});
</script>

<template>
  <section class="page-heading">
    <div class="th-main">
      <h1>My account</h1>
      <p>Manage your profile and password.</p>
    </div>
    <router-link :to="{ name: 'orders' }" class="text-button">
      My orders <Icon name="arrow" :size="15" />
    </router-link>

      <div class="th-cell"><small>Sheet</small><b>ACCOUNT-01</b></div>
      <div class="th-cell"><small>Member</small><b>{{ user?.id }}</b></div>
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

  <div class="account-grid">
    <section class="data-panel" aria-label="Edit profile">
      <div class="panel-header">
        <div>
          <h2>Profile</h2>
          <p>Update your member information.</p>
        </div>
      </div>
      <div class="notify-form">
        <label class="account-label" for="account-name">Name</label>
        <input
          id="account-name"
          v-model="profileForm.name"
          class="row-edit-field"
          type="text"
          aria-label="Your name"
        />
        <label class="account-label" for="account-email">Email</label>
        <input
          id="account-email"
          v-model="profileForm.email"
          class="row-edit-field"
          type="email"
          aria-label="Your email"
        />
        <div class="order-actions">
          <button
            type="button"
            class="primary-button"
            :disabled="profileBusy || !profileDirty"
            @click="saveProfile"
          >
            Save changes
          </button>
        </div>
      </div>
    </section>

    <section ref="passwordSection" class="data-panel" aria-label="Change password">
      <div class="panel-header">
        <div>
          <h2>Password</h2>
          <p>8–128 characters. Changing it signs you out everywhere.</p>
        </div>
      </div>
      <div class="notify-form">
        <label class="account-label" for="account-password">New password</label>
        <input
          id="account-password"
          v-model="passwordForm.next"
          class="row-edit-field"
          type="password"
          autocomplete="new-password"
          aria-label="New password"
        />
        <label class="account-label" for="account-password-confirm">Confirm new password</label>
        <input
          id="account-password-confirm"
          v-model="passwordForm.confirm"
          class="row-edit-field"
          type="password"
          autocomplete="new-password"
          aria-label="Confirm new password"
        />
        <div class="order-actions">
          <button
            type="button"
            class="primary-button"
            :disabled="passwordBusy"
            @click="changePassword"
          >
            Change password
          </button>
        </div>
      </div>
    </section>
  </div>
</template>
