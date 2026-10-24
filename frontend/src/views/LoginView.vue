<script setup lang="ts">
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import Icon from "@/components/Icon.vue";
import { useAuth } from "@/stores/auth";
import { useTheme } from "@/stores/theme";
import { LoginFormSchema } from "@/lib/schemas";

// 登入頁 —— Tailwind utilities 的遷移範本（tokens 經 @theme 引 var()，
// dark mode 靠 [data-theme] 翻轉，utilities 自動跟著變）。
// 表單以 zod 驗證（email 格式 / 密碼必填），錯誤 inline 顯示在欄位下。

const route = useRoute();
const router = useRouter();

const { login } = useAuth();
const { theme, toggleTheme } = useTheme();

const email = ref("");
const password = ref("");
const error = ref("");
const fieldErrors = ref<Record<string, string>>({});
const submitting = ref(false);

// 改密碼成功後被導回來（/login?changed=1）：顯示持久確認。
const passwordChanged = route.query.changed === "1";

async function handleSubmit(): Promise<void> {
  error.value = "";

  // 前端先驗：不合契約不打 API。
  const parsed = LoginFormSchema.safeParse({ email: email.value, password: password.value });
  if (!parsed.success) {
    fieldErrors.value = Object.fromEntries(
      parsed.error.issues.map((issue) => [String(issue.path[0] ?? ""), issue.message]),
    );
    return;
  }
  fieldErrors.value = {};

  submitting.value = true;

  try {
    await login(parsed.data.email, parsed.data.password);

    // 登入成功 → 回到原本想去的頁面（守衛帶進來的 redirect）或店面（F2-1：進入 /）。
    const redirect = route.query.redirect;
    // 只接受站內路徑（以單一 / 開頭，排除 // 協議相對路徑），避免 open redirect。
    const target =
      typeof redirect === "string" && redirect.startsWith("/") && !redirect.startsWith("//")
        ? redirect
        : "/";
    await router.push(target);
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
  <div class="relative grid min-h-screen place-items-center bg-paper px-6 py-10">
    <button
      type="button"
      class="absolute top-5 right-5 grid h-[34px] w-[34px] place-items-center rounded-lg border border-line-strong text-ink-soft transition-colors hover:border-brand hover:text-ink"
      :aria-label="theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'"
      @click="toggleTheme"
    >
      <Icon :name="theme === 'dark' ? 'sun' : 'moon'" :size="15" />
    </button>

    <div class="w-full max-w-[400px]">
      <div class="mb-6 flex items-center gap-3 font-bold tracking-tight text-ink-strong">
        <span class="grid h-8 w-8 place-items-center rounded-lg bg-brand text-on-brand">
          <Icon name="bolt" :size="16" />
        </span>
        <span>Backend Lab</span>
      </div>

      <div class="rounded-2xl border border-line bg-card p-9 shadow-[0_18px_44px_rgba(62,55,44,0.16)]">
        <h1 class="m-0 text-[21px] font-bold tracking-tight text-ink-strong">Sign in</h1>
        <p class="mt-1.5 mb-5 text-[12.5px] text-ink-soft">
          Use your Backend Lab account to access the workspace.
        </p>

        <p
          v-if="passwordChanged"
          role="status"
          class="mb-3.5 rounded-lg border border-[#cdddd0] bg-success-bg px-3 py-2.5 text-xs text-success-ink"
        >
          Password changed — sign in with your new password.
        </p>

        <p
          v-if="error"
          role="alert"
          class="mb-3.5 rounded-lg border border-[#e3c4ba] bg-danger-bg px-3 py-2.5 text-xs text-danger-ink"
        >
          {{ error }}
        </p>

        <form class="flex flex-col gap-3.5" novalidate @submit.prevent="handleSubmit">
          <div class="flex flex-col gap-1.5">
            <label for="email" class="text-[11px] font-semibold text-ink-soft">Email</label>
            <input
              id="email"
              v-model="email"
              type="email"
              autocomplete="username"
              placeholder="you@example.com"
              class="h-10 rounded-lg border border-line bg-card px-3 text-[13px] text-ink outline-none caret-ink placeholder:text-ink-faint focus:border-brand"
            />
            <p v-if="fieldErrors.email" class="m-0 text-[11px] text-danger-ink">
              {{ fieldErrors.email }}
            </p>
          </div>

          <div class="flex flex-col gap-1.5">
            <label for="password" class="text-[11px] font-semibold text-ink-soft">Password</label>
            <input
              id="password"
              v-model="password"
              type="password"
              autocomplete="current-password"
              placeholder="••••••••"
              class="h-10 rounded-lg border border-line bg-card px-3 text-[13px] text-ink outline-none caret-ink placeholder:text-ink-faint focus:border-brand"
            />
            <p v-if="fieldErrors.password" class="m-0 text-[11px] text-danger-ink">
              {{ fieldErrors.password }}
            </p>
          </div>

          <button
            type="submit"
            class="mt-1 grid h-10 place-items-center rounded-lg bg-brand text-xs font-semibold text-on-brand transition-colors hover:bg-brand-strong disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="submitting"
          >
            {{ submitting ? "Signing in..." : "Sign in" }}
          </button>
        </form>

        <p class="mt-5 mb-0 text-center text-[11px] text-ink-faint">
          Protected by session cookies · HttpOnly · SameSite
        </p>
      </div>
    </div>
  </div>
</template>
