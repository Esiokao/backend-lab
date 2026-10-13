<script setup lang="ts">
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import Icon from "@/components/Icon.vue";
import { useAuth } from "@/stores/auth";

const route = useRoute();
const router = useRouter();

const { login } = useAuth();

const email = ref("");
const password = ref("");
const error = ref("");
const submitting = ref(false);

async function handleSubmit(): Promise<void> {
  error.value = "";
  submitting.value = true;

  try {
    await login(email.value, password.value);

    // 登入成功 → 回到原本想去的頁面（守衛帶進來的 redirect）或儀表板。
    const redirect = route.query.redirect;
    await router.push(typeof redirect === "string" ? redirect : { name: "dashboard" });
  } catch (err) {
    error.value =
      err instanceof Error && err.message.includes("Invalid")
        ? "Invalid email or password"
        : "Login failed. Please try again.";
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <div class="login-shell">
    <div class="login-card">
      <div class="login-brand">
        <span class="brand-mark"><Icon name="bolt" :size="16" /></span>
        <span>Backend Lab</span>
      </div>

      <h1>Sign in</h1>
      <p>Use your Backend Lab account to access the workspace.</p>

      <p v-if="error" class="login-error" role="alert">{{ error }}</p>

      <form @submit.prevent="handleSubmit">
        <div class="login-field">
          <label for="email">Email</label>
          <input
            id="email"
            v-model="email"
            type="email"
            autocomplete="username"
            placeholder="you@example.com"
            required
          />
        </div>

        <div class="login-field">
          <label for="password">Password</label>
          <input
            id="password"
            v-model="password"
            type="password"
            autocomplete="current-password"
            placeholder="••••••••"
            required
          />
        </div>

        <button type="submit" class="login-submit" :disabled="submitting">
          <Icon name="shield" :size="15" />
          {{ submitting ? "Signing in..." : "Sign in" }}
        </button>
      </form>

      <p class="login-footer">Protected by session cookies · HttpOnly · SameSite</p>
    </div>
  </div>
</template>
