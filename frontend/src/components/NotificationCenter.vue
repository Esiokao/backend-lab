<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter, type RouteLocationRaw } from "vue-router";

import Icon from "@/components/Icon.vue";
import { useAuth } from "@/stores/auth";
import { useNotifications, type NotificationItem } from "@/stores/notifications";
import { usePopover } from "@/stores/popover";

// 通知鈴鐺 + 面板（F11）：可嵌入任何 header（workspace topbar / 店面 header）。
// 元件擁有輪詢生命週期（登入期間開、卸載停）；面板開啟時 Esc 可收。
// General = 個人通知（計未讀）；System = 廣播公告。

const route = useRoute();
const router = useRouter();
const { user } = useAuth();
const { active: activePopover, openPopover, closePopover } = usePopover();
const {
  unreadCount,
  broadcastsUnread,
  items: notifications,
  broadcasts,
  panelOpen,
  startPolling,
  stopPolling,
  togglePanel,
  markRead,
  markAllRead,
  markAllBroadcastsRead,
} = useNotifications();

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString();
}

// 點通知 → 對應頁面：order_created/order_paid 帶 data.order_id → 訂單詳情；
// product_restocked 帶 data.product_id → 店面（補貨的商品在那裡可買）。
function notificationTarget(notification: NotificationItem): RouteLocationRaw | null {
  const orderId = Number(notification.data?.order_id);
  if (Number.isInteger(orderId) && orderId > 0) {
    return { name: "order-detail", params: { id: orderId } };
  }
  const productId = Number(notification.data?.product_id);
  if (Number.isInteger(productId) && productId > 0) {
    return { name: "storefront" };
  }
  return null;
}

// 點擊 = 標已讀 + 導向（無目標就只標已讀）。
async function openNotification(notification: NotificationItem): Promise<void> {
  markRead(notification);
  const target = notificationTarget(notification);
  if (target) {
    panelOpen.value = false;
    await router.push(target);
  }
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

// workspace 內換頁時本元件不卸載：跟著路由收面板。
watch(
  () => route.fullPath,
  () => {
    if (panelOpen.value) panelOpen.value = false;
  },
);

// 互斥：面板開 → 登記為作用中；別的浮層開 → 收面板。
watch(panelOpen, (open) => {
  if (open) openPopover("notifications");
  else closePopover("notifications");
});
watch(activePopover, (name) => {
  if (name !== null && name !== "notifications" && panelOpen.value) {
    panelOpen.value = false;
  }
});

function onKeydown(event: KeyboardEvent): void {
  if (event.key === "Escape" && panelOpen.value) panelOpen.value = false;
}
</script>

<template>
  <div class="bell-wrap">
    <button type="button" class="bell-button" aria-label="Notifications" @click="togglePanel">
      <Icon name="bell" :size="17" />
      <span v-if="unreadCount + broadcastsUnread > 0" class="bell-badge">
        {{ unreadCount + broadcastsUnread > 99 ? "99+" : unreadCount + broadcastsUnread }}
      </span>
    </button>
    <div v-if="panelOpen" class="notif-panel" role="dialog" aria-label="Notifications panel">
      <div class="notif-panel-header">
        <strong>Notifications</strong>
        <div class="notif-panel-actions">
          <button
            v-if="notifTab === 'general' && unreadCount > 0"
            type="button"
            class="text-button"
            @click="markAllRead"
          >
            Mark all as read
          </button>
          <button
            v-if="notifTab === 'broadcast' && broadcastsUnread > 0"
            type="button"
            class="text-button"
            @click="markAllBroadcastsRead"
          >
            Mark all as read
          </button>
          <button type="button" class="row-action" aria-label="Close notifications" @click="togglePanel">
            <Icon name="close" :size="14" />
          </button>
        </div>
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
                @click="openNotification(notification)"
              >
                <span class="notif-title">
                  <i v-if="notification.read_at === null" class="notif-dot" />{{ notification.title }}
                </span>
                <span class="notif-body">{{ notification.body }}</span>
                <span class="notif-time">
                  {{ formatTime(notification.created_at) }}
                  <Icon
                    v-if="notificationTarget(notification)"
                    name="arrow"
                    :size="11"
                    class="notif-go"
                  />
                </span>
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
      <!-- 分頁列放在清單下面：先讀內容、再切類型（清單是主角）。 -->
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
          <span v-if="broadcastsUnread > 0" class="notif-tab-badge">{{ broadcastsUnread }}</span>
        </button>
      </div>
    </div>
  </div>
</template>
