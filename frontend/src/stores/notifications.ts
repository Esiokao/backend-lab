import { ref } from "vue";

import { api } from "@/lib/api";

// 站內通知 store（F11）：鈴鐺徽章輪詢 + 通知面板資料。
// - 表為真相來源：未讀數由 /notifications/unread-count 補齊（F11-6）
// - admin 的 SSE 即時推送（F11-4）等後端端點存在後再接，屆時只需在此 store 加訂閱
// - 輪詢間隔 10s，與 API Health 頁一致

export type NotificationItem = {
  id: number;
  type: string;
  title: string;
  body: string;
  data: Record<string, unknown>;
  created_at: string;
  read_at: string | null;
};

// admin 廣播公告（GET /notifications/broadcasts，全使用者可見的公告表）。
export type BroadcastItem = {
  id: number;
  type: string;
  title: string;
  body: string;
  created_at: string;
};

const POLL_INTERVAL_MS = 10_000;

const unreadCount = ref(0);
const items = ref<NotificationItem[]>([]);
const broadcasts = ref<BroadcastItem[]>([]);
const panelOpen = ref(false);

let timer: number | undefined;
let polling = false;

async function refreshUnread(): Promise<void> {
  try {
    const data = await api.get<{ unread_count: number }>("/notifications/unread-count");
    unreadCount.value = data.unread_count;
  } catch {
    // 輪詢失敗靜默，下一輪再試（不讓暫時性故障打擾使用者）。
  }
}

async function refreshList(): Promise<void> {
  try {
    const data = await api.get<{ items: NotificationItem[] }>("/notifications?limit=20");
    items.value = data.items;
  } catch {
    // 同上。
  }
}

async function loadBroadcasts(): Promise<void> {
  try {
    const data = await api.get<{ items: BroadcastItem[] }>("/notifications/broadcasts");
    broadcasts.value = data.items;
  } catch {
    // 公告抓不到不影響個人通知列表。
  }
}

async function markRead(notification: NotificationItem): Promise<void> {
  if (notification.read_at !== null) return;

  try {
    await api.patch(`/notifications/${notification.id}/read`, {});
    notification.read_at = new Date().toISOString();
    unreadCount.value = Math.max(0, unreadCount.value - 1);
  } catch {
    // 靜默。
  }
}

async function markAllRead(): Promise<void> {
  try {
    await api.patch("/notifications/mark_all_read", {});
    items.value.forEach((item) => {
      if (item.read_at === null) item.read_at = new Date().toISOString();
    });
    unreadCount.value = 0;
  } catch {
    // 靜默。
  }
}

function scheduleNext(): void {
  if (!polling) return;

  timer = window.setTimeout(async () => {
    await refreshUnread();
    // 面板開著時順便刷新清單。
    if (panelOpen.value) await refreshList();
    scheduleNext();
  }, POLL_INTERVAL_MS);
}

function startPolling(): void {
  if (polling) return;
  polling = true;

  void refreshUnread();
  scheduleNext();
}

function stopPolling(): void {
  polling = false;
  if (timer !== undefined) {
    window.clearTimeout(timer);
    timer = undefined;
  }
}

function togglePanel(): void {
  panelOpen.value = !panelOpen.value;
  // 每次打開都抓最新清單（含公告）。
  if (panelOpen.value) {
    void refreshList();
    void loadBroadcasts();
  }
}

export function useNotifications() {
  return {
    unreadCount,
    items,
    broadcasts,
    panelOpen,
    startPolling,
    stopPolling,
    togglePanel,
    refreshList,
    loadBroadcasts,
    markRead,
    markAllRead,
  };
}
