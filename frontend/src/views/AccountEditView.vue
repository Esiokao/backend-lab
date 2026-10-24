<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import Icon from "@/components/Icon.vue";
import { ApiError, api } from "@/lib/api";
import { PasswordFormSchema, ProfileFormSchema } from "@/lib/schemas";
import { useAuth } from "@/stores/auth";
import { useToast } from "@/stores/toast";

// 會員資料編輯（/app/account/edit）：
// - 會員資料修改（PATCH /users/{id}，本人）—— 儲存後回唯讀頁
// - 修改密碼（PATCH /users/{id} 帶 password → 後端撤銷全部 session，含本機）：
//   成功後強制重新登入（登入頁顯示 ?changed=1 橫幅）。
// - ?section=password 直接聚焦修改密碼（下拉選單的 Change password 入口）。

const route = useRoute();
const router = useRouter();
const toast = useToast();
const { user, setUser, logout } = useAuth();

// ── 會員資料修改 ──
const profileForm = ref({ name: "", email: "" });
const profileErrors = ref<Record<string, string>>({});
const profileBusy = ref(false);
const profileDirty = computed(
  () =>
    profileForm.value.name !== (user.value?.name ?? "") ||
    profileForm.value.email !== (user.value?.email ?? ""),
);

async function saveProfile(): Promise<void> {
  if (!user.value) return;

  const parsed = ProfileFormSchema.safeParse({
    name: profileForm.value.name,
    email: profileForm.value.email,
  });
  if (!parsed.success) {
    profileErrors.value = Object.fromEntries(
      parsed.error.issues.map((issue) => [String(issue.path[0] ?? ""), issue.message]),
    );
    return;
  }
  profileErrors.value = {};
  const { name, email } = parsed.data;

  profileBusy.value = true;
  try {
    const updated = await api.patch<{ id: number; name: string; email: string; role: "user" | "admin" }>(
      `/users/${user.value.id}`,
      { name, email },
    );
    setUser({ ...user.value, name: updated.name, email: updated.email });
    toast.show("Profile updated.");
    // 改完回唯讀頁看結果。
    await router.push({ name: "account" });
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
const passwordErrors = ref<Record<string, string>>({});
const passwordBusy = ref(false);
const passwordSection = ref<HTMLElement | null>(null);

async function changePassword(): Promise<void> {
  if (!user.value) return;

  const parsed = PasswordFormSchema.safeParse({
    next: passwordForm.value.next,
    confirm: passwordForm.value.confirm,
  });
  if (!parsed.success) {
    passwordErrors.value = Object.fromEntries(
      parsed.error.issues.map((issue) => [String(issue.path[0] ?? ""), issue.message]),
    );
    return;
  }
  passwordErrors.value = {};
  const { next } = parsed.data;

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

  // 下拉選單的 Change password 入口：/app/account/edit?section=password
  if (route.query.section === "password") {
    passwordSection.value?.scrollIntoView({ behavior: "smooth", block: "start" });
  }
});
</script>

<template>
  <section class="page-heading">
    <div class="th-main">
      <h1>Edit profile</h1>
      <p>Update your member information or change your password.</p>
    </div>
    <router-link :to="{ name: 'account' }" class="text-button">
      <Icon name="arrow" :size="15" /> Back to account
    </router-link>
    <div class="th-cell"><small>Sheet</small><b>ACCOUNT-02</b></div>
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
        <p v-if="profileErrors.name" class="field-error">{{ profileErrors.name }}</p>
        <label class="account-label" for="account-email">Email</label>
        <input
          id="account-email"
          v-model="profileForm.email"
          class="row-edit-field"
          type="email"
          aria-label="Your email"
        />
        <p v-if="profileErrors.email" class="field-error">{{ profileErrors.email }}</p>
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
        <p v-if="passwordErrors.next" class="field-error">{{ passwordErrors.next }}</p>
        <label class="account-label" for="account-password-confirm">Confirm new password</label>
        <input
          id="account-password-confirm"
          v-model="passwordForm.confirm"
          class="row-edit-field"
          type="password"
          autocomplete="new-password"
          aria-label="Confirm new password"
        />
        <p v-if="passwordErrors.confirm" class="field-error">{{ passwordErrors.confirm }}</p>
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
