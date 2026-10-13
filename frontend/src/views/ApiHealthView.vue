<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";

import Icon from "@/components/Icon.vue";
import { api } from "@/lib/api";

// 健康檢查回傳格式。
type Health = { status: string };

const live = ref<boolean | null>(null);
const ready = ref<boolean | null>(null);
const lastChecked = ref("");
const refreshing = ref(false);

// 自動輪詢的 timer（unmount 時清理）。
let timer: number | undefined;

// 單一端點探測：成功且 status 為 ok 才算 Operational。
async function probe(path: string): Promise<boolean> {
  try {
    const res = await api.get<Health>(path);
    return res.status === "ok";
  } catch {
    return false;
  }
}

async function refresh(): Promise<void> {
  refreshing.value = true;
  try {
    const [h, r] = await Promise.all([probe("/health"), probe("/ready")]);
    live.value = h;
    ready.value = r;
    lastChecked.value = new Date().toLocaleTimeString();
  } finally {
    refreshing.value = false;
  }
}

onMounted(() => {
  void refresh();
  // 每 10 秒自動刷新。
  timer = window.setInterval(() => {
    void refresh();
  }, 10000);
});

onUnmounted(() => {
  if (timer !== undefined) window.clearInterval(timer);
});
</script>

<template>
  <section class="page-heading">
    <div>
      <p class="eyebrow">System workspace</p>
      <h1>API Health</h1>
      <p>Live status of the backend services.</p>
    </div>
    <button class="primary-button" :disabled="refreshing" @click="refresh">
      <Icon name="activity" :size="15" />
      {{ refreshing ? "Checking..." : "Refresh" }}
    </button>
  </section>

  <section class="metrics" aria-label="API status">
    <article class="metric-card">
      <div class="metric-top">
        <span class="metric-icon green"><Icon name="server" /></span>
        <span v-if="live === true" class="health-badge"><i /> Operational</span>
        <span v-else-if="live === false" class="health-badge" style="color: #f87171">
          <i style="background: #f87171" /> Down
        </span>
        <span v-else class="latency">checking...</span>
      </div>
      <p>Liveness</p>
      <strong>{{ live === null ? "—" : live ? "Operational" : "Down" }}</strong>
      <small>GET /api/health</small>
    </article>

    <article class="metric-card">
      <div class="metric-top">
        <span class="metric-icon cyan"><Icon name="database" /></span>
        <span v-if="ready === true" class="health-badge"><i /> Operational</span>
        <span v-else-if="ready === false" class="health-badge" style="color: #f87171">
          <i style="background: #f87171" /> Down
        </span>
        <span v-else class="latency">checking...</span>
      </div>
      <p>Readiness</p>
      <strong>{{ ready === null ? "—" : ready ? "Operational" : "Down" }}</strong>
      <small>GET /api/ready</small>
    </article>
  </section>

  <section class="security-strip">
    <span class="security-icon"><Icon name="shield" :size="20" /></span>
    <div>
      <strong>Auto-refresh every 10 seconds</strong>
      <p>
        Last checked:
        {{ lastChecked === "" ? "never" : lastChecked }}
      </p>
    </div>
  </section>
</template>
