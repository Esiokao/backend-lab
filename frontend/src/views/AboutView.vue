<script setup lang="ts">
import StorefrontHeader from "@/components/StorefrontHeader.vue";
import StorefrontFooter from "@/components/StorefrontFooter.vue";

// About us（/about）：這個 repo 的技術棧與工程實踐。
// 新頁面慣例：Tailwind utilities + token 主題（dark mode 隨 [data-theme] 自動翻）。

const backend = [
  ["Framework", "FastAPI"],
  ["ORM / Migrations", "SQLAlchemy · Alembic"],
  ["Database", "PostgreSQL 17"],
  ["Cache / Rate limit", "Redis 7"],
  ["Background jobs", "RQ（outbox → notifications worker）"],
  ["Validation", "Pydantic"],
  ["Tests", "pytest（220+ cases）"],
];

const frontend = [
  ["Framework", "Vue 3.5（Composition API + <script setup>）"],
  ["Language", "TypeScript 6（vue-tsc，掛 pre-commit）"],
  ["Build", "Vite 8"],
  ["Routing", "vue-router 4（角色化守衛）"],
  ["Styling", "Tailwind CSS v4（token @theme）＋ 純 CSS 設計系統"],
  ["Validation", "zod（API 契約 runtime 驗證 ＋ 表單 inline errors）"],
  ["API client", "手寫 fetch 包裝（ApiError / SchemaError）"],
  ["State", "手寫 composable stores（無 Pinia）"],
];

const infra = [
  ["Containers", "Docker Compose（api / postgres / redis / workers / nginx）"],
  ["Edge", "nginx（TLS 終結、HSTS）"],
  ["CI/CD", "GitHub Actions：test → build → GHCR → SSH deploy → smoke test"],
];

const auth = [
  ["Session", "HttpOnly · Secure · SameSite=strict cookie"],
  ["Expiry", "7 天滑動過期（Redis）"],
  ["Revocation", "改密碼撤銷全部 session（含跨裝置演示）"],
  ["Rate limit", "登入 5 次/60s（Redis Lua 原子化）"],
];

const design = [
  ["World", "Engineering Vellum（圖紙標題塊 / 蓋章徽章 / 製圖網格）"],
  ["Themes", "奶油紙 light ＋ 暖炭黑 dark（token 翻轉，零 dark: variant）"],
  ["Type", "DM Sans ＋ JetBrains Mono（數據 tabular）"],
  ["Tokens", "CSS custom properties 單一真相（DESIGN.md）"],
];
</script>

<template>
  <StorefrontHeader />

  <main class="mx-auto w-[min(1180px,calc(100%-80px))] pb-16 pt-11">
    <!-- 標題塊（world 一致格式） -->
    <section
      class="mb-7 flex items-stretch overflow-hidden rounded-sm border-[1.5px] border-brand bg-card"
    >
      <div class="flex-1 px-[22px] pb-3.5 pt-4">
        <h1 class="m-0 text-[28px] font-bold tracking-tight text-ink-strong">About us</h1>
        <p class="mt-1.5 text-[13px] text-ink-soft">
          What this repo is built with — the whole stack, honestly listed.
        </p>
      </div>
      <div class="flex flex-col justify-center border-l border-line px-[22px]">
        <small
          class="text-[9px] font-bold uppercase tracking-[0.14em] text-ink-faint"
        >
          Sheet
        </small>
        <b class="font-mono text-[12.5px] font-semibold tabular-nums text-ink-strong">
          ABOUT-01
        </b>
      </div>
    </section>

    <section class="mb-7 rounded-xl border border-line bg-card px-[23px] py-5">
      <p class="m-0 max-w-[75ch] text-[13px] leading-relaxed text-ink">
        <strong class="text-ink-strong">Backend Lab</strong> is a fullstack engineering demo:
        a public storefront with cart &amp; checkout, a member center, and an admin workspace —
        wired end-to-end to a FastAPI backend with session auth, RBAC, an order state machine,
        and RQ-driven notifications. Every number on screen comes from the real API; nothing is
        decorative.
      </p>
    </section>

    <div class="grid grid-cols-1 gap-3.5 lg:grid-cols-2">
      <section
        v-for="section in [
          { title: 'Backend', rows: backend },
          { title: 'Frontend', rows: frontend },
          { title: 'Auth & security', rows: auth },
          { title: 'Infrastructure', rows: infra },
          { title: 'Design system', rows: design },
        ]"
        :key="section.title"
        class="overflow-hidden rounded-xl border border-line bg-card"
      >
        <div class="border-b border-line-soft px-[23px] py-4">
          <h2 class="m-0 text-[15px] font-semibold text-ink-strong">{{ section.title }}</h2>
        </div>
        <dl class="m-0 px-[23px] py-2">
          <div
            v-for="row in section.rows"
            :key="row[0]"
            class="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-0.5 border-b border-line-soft py-3 last:border-b-0"
          >
            <dt
              class="text-[10px] font-bold uppercase tracking-[0.1em] text-ink-faint"
            >
              {{ row[0] }}
            </dt>
            <dd class="m-0 text-right text-[12.5px] font-semibold break-all text-ink">
              {{ row[1] }}
            </dd>
          </div>
        </dl>
      </section>
    </div>
  </main>

  <StorefrontFooter />
</template>
