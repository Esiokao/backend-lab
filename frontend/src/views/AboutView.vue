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
  ["Background jobs", "RQ (outbox → notifications worker)"],
  ["Validation", "Pydantic"],
];

const frontend = [
  ["Stack", "Vue 3.5 · TypeScript · Vite"],
  ["Routing", "vue-router (role-based guards)"],
  ["Styling", "Tailwind CSS v4 (token @theme)"],
  ["Validation", "zod (runtime API contract + form errors)"],
  ["State", "hand-rolled composable stores"],
];

const infra = [
  ["Cloud", "AWS EC2 (full stack on docker compose)"],
  ["Edge / DNS", "nginx (TLS, HSTS) · Cloudflare (DNS + proxy)"],
  ["CI/CD", "GitHub Actions: test → build → GHCR → deploy"],
  ["Deploy flow", "staging auto on green CI → production manual approval → smoke test"],
  ["Rollback", "immutable per-sha images on GHCR; redeploy old sha"],
];

const testing = [
  ["Backend", "pytest integration (220+ cases)"],
  ["E2E", "Playwright journeys (shopper + admin)"],
  ["Load", "k6 (in progress)"],
  ["Post-deploy", "smoke tests against production"],
];

const auth = [
  ["Session", "HttpOnly · Secure · SameSite=strict cookie"],
  ["Expiry", "7-day sliding (Redis)"],
  ["Revocation", "password change revokes all sessions"],
  ["Rate limit", "login 5 per 60s (Redis, atomic Lua)"],
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
      <p class="m-0 text-[13px] leading-relaxed text-ink">
        <strong class="text-ink-strong">Backend Lab</strong> is a fullstack e-commerce demo built
        to practice engineering: a real API under everything you see, automated tests, and a full
        CI/CD pipeline. Nothing on screen is decorative.
      </p>
    </section>

    <div class="grid grid-cols-1 items-start gap-3.5 lg:grid-cols-2">
      <section
        v-for="section in [
          { title: 'Backend', rows: backend },
          { title: 'Frontend', rows: frontend },
          { title: 'Auth & security', rows: auth },
          { title: 'Testing', rows: testing },
          { title: 'Infrastructure & CI/CD', rows: infra },
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
