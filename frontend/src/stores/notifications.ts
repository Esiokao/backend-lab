import { ref } from "vue";

import { z } from "zod";

import { api } from "@/lib/api";
import {
  BroadcastSchema,
  NotificationItemSchema,
  UnreadCountSchema,
  type Broadcast,
  type NotificationItem,
} from "@/lib/schemas";

// 站內通知 store（F11）：鈴鐺徽章輪詢 + 通知面板資料。
// - 表為真相來源：未讀數由 /notifications/unread-count 補齊（F11-6）
// - 即時推送（F11-4）：登入期間開一條 SSE，收到事件只當「該刷新了」的提醒，
//   資料一律重新 GET——推送漏了有輪詢兜底，輪詢在 SSE 連著時自動降頻
// - 輪詢間隔動態：SSE 連著 30s（兜底）／斷線 10s（原節奏）

// 清單回應包裝（items + next_cursor）；廣播公告 GET /notifications/broadcasts。
const NotificationListSchema = z.object({
  items: z.array(NotificationItemSchema),
  next_cursor: z.string().nullable().optional(),
});
const BroadcastListSchema = z.object({
  items: z.array(BroadcastSchema),
  unread_count: z.number().int(),
});

const SSE_POLL_INTERVAL_MS = 30_000; // SSE 連著：輪詢只是保險
const FALLBACK_POLL_INTERVAL_MS = 10_000; // SSE 斷線：回到原節奏

const unreadCount = ref(0);
const broadcastsUnread = ref(0);
const items = ref<NotificationItem[]>([]);
const broadcasts = ref<Broadcast[]>([]);
const panelOpen = ref(false);

let timer: number | undefined;
let polling = false;
let pollIntervalMs = FALLBACK_POLL_INTERVAL_MS;
let eventSource: EventSource | undefined;

async function refreshUnread(): Promise<void> {
  try {
    const data = await api.get("/notifications/unread-count", UnreadCountSchema);
    unreadCount.value = data.unread_count;
    broadcastsUnread.value = data.broadcasts_unread;
  } catch {
    // 輪詢失敗靜默，下一輪再試（不讓暫時性故障打擾使用者）。
  }
}

async function refreshList(): Promise<void> {
  try {
    const data = await api.get("/notifications?limit=20", NotificationListSchema);
    items.value = data.items;
  } catch {
    // 同上。
  }
}

async function loadBroadcasts(): Promise<void> {
  try {
    const data = await api.get("/notifications/broadcasts", BroadcastListSchema);
    broadcasts.value = data.items;
    broadcastsUnread.value = data.unread_count;
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

// 廣播已讀（v1.12 水位法）：全有全無，伺服器推水位到最新。
async function markAllBroadcastsRead(): Promise<void> {
  try {
    await api.post("/notifications/broadcasts/read-all");
    broadcastsUnread.value = 0;
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
  }, pollIntervalMs);
}

// ── SSE（F11-4）：登入期間常駐的即時推送連線 ──
// EventSource 不能走 api.ts（那是 fetch 包裝）；同源 + cookie 自動帶，
// 直接 new 即可。收到任何事件都只當「提醒」，資料重新 GET。
function startEventSource(): void {
  if (eventSource) return;

  eventSource = new EventSource("/api/notifications/stream");

  // 後端開場事件：連線確立 → 輪詢降頻 + 立刻對一次錶。
  eventSource.addEventListener("connected", () => {
    pollIntervalMs = SSE_POLL_INTERVAL_MS;
    void refreshUnread();
  });

  // 通知／公告都推這個事件名稱：徽章即時跳號；面板開著才多刷清單。
  eventSource.addEventListener("notification", () => {
    void refreshUnread();
    if (panelOpen.value) void refreshList();
  });

  // 斷線：回到 10 秒兜底節奏。EventSource 會自動重連，
  // 連上後 "connected" 事件會再把節奏放寬——這裡不需要重連邏輯。
  eventSource.onerror = () => {
    pollIntervalMs = FALLBACK_POLL_INTERVAL_MS;
  };
}

function stopEventSource(): void {
  eventSource?.close();
  eventSource = undefined;
  pollIntervalMs = FALLBACK_POLL_INTERVAL_MS;
}

function startPolling(): void {
  if (polling) return;
  polling = true;

  startEventSource();
  void refreshUnread();
  scheduleNext();
}

function stopPolling(): void {
  polling = false;
  stopEventSource();
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

export type { NotificationItem } from "@/lib/schemas";

export function useNotifications() {
  return {
    unreadCount,
    broadcastsUnread,
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
    markAllBroadcastsRead,
  };
}
