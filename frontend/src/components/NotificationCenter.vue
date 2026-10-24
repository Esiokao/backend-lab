<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from "vue";

import Icon from "@/components/Icon.vue";
import { useAuth } from "@/stores/auth";
import { useNotifications } from "@/stores/notifications";

// 通知鈴鐺 + 面板（F11）：可嵌入任何 header（workspace topbar / 店面 header）。
// 元件擁有輪詢生命週期（登入期間開、卸載停）；面板開啟時 Esc 可收。
// General = 個人通知（計未讀）；System = 廣播公告。

const { user } = useAuth();
const {
  unreadCount,
  items: notifications,
  broadcasts,
  panelOpen,
  startPolling,
  stopPolling,
  togglePanel,
  markRead,
  markAllRead,
} = useNotifications();

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString();
}

// 分頁：一般通知（個人、可標已讀）／廣播（系統公告）。開面板時回到 General。
const notifTab = ref<"general" | "broadcast">("general");

watch(panelOpen, (open) => {
  if (open) notifTab.value = "general";
});

// 跨頁導航會卸載本元件：收起面板，避免下個頁面的鈴鐺帶著開啟狀態。
onUnmounted(() => {
  stopPolling();
  if (panelOpen.value) panelOpen.value = false;
  document.removeEventListener("keydown", onKeydown);
});

onMounted(() => {
  if (user.value) startPolling();
  document.addEventListener("keydown", onKeydown);
});

watch(user, (value) => {
  if (value) startPolling();
  else stopPolling();
});

function onKeydown(event: KeyboardEvent): void {
  if (event.key === "Escape" && panelOpen.value) panelOpen.value = false;
}
</script>

<template>
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
          <button
            v-if="notifTab === 'general'"
            type="button"
            class="text-button"
            @click="markAllRead"
          >
            Mark all read
          </button>
          <button type="button" class="row-action" aria-label="Close notifications" @click="togglePanel">
            <Icon name="close" :size="14" />
          </button>
        </div>
      </div>
      <div class="notif-tabs" role="tablist" aria-label="Notification type">
        <button
          type="button"
          role="tab"
          :aria-selected="notifTab === 'general'"
          :class="['notif-tab', { active: notifTab === 'general' }]"
          @click="notifTab = 'general'"
        >
          General
          <span v-if="unreadCount > 0" class="notif-tab-badge">
            {{ unreadCount > 99 ? "99+" : unreadCount }}
          </span>
        </button>
        <button
          type="button"
          role="tab"
          :aria-selected="notifTab === 'broadcast'"
          :class="['notif-tab', { active: notifTab === 'broadcast' }]"
          @click="notifTab = 'broadcast'"
        >
          System
          <span v-if="broadcasts.length > 0" class="notif-tab-badge">{{ broadcasts.length }}</span>
        </button>
      </div>
      <div class="notif-panel-body">
        <div v-if="notifTab === 'general'">
          <p v-if="notifications.length === 0" class="notif-empty">
            No general notifications yet.
          </p>
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
        <div v-else>
          <p v-if="broadcasts.length === 0" class="notif-empty">
            No system broadcasts yet.
          </p>
          <ul v-else class="notif-list">
            <li v-for="broadcast in broadcasts" :key="broadcast.id">
              <div class="notif-item broadcast">
                <span class="notif-title">{{ broadcast.title }}</span>
                <span class="notif-body">{{ broadcast.body }}</span>
                <span class="notif-time">{{ formatTime(broadcast.created_at) }}</span>
              </div>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>
