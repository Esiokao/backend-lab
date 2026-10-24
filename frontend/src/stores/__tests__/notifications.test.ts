import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// notifications store：徽章數學（未讀遞減、地板 0、全部已讀）。
vi.mock("@/lib/api", () => ({
  api: {
    get: vi.fn(),
    patch: vi.fn(),
  },
}));

import { api } from "@/lib/api";

type NotifItem = {
  id: number;
  type: string;
  title: string;
  body: string;
  data: Record<string, unknown>;
  created_at: string;
  read_at: string | null;
};

type NotifApi = {
  useNotifications: () => {
    unreadCount: { value: number };
    items: { value: NotifItem[] };
    markRead: (n: NotifItem) => Promise<void>;
    markAllRead: () => Promise<void>;
  };
};

function unread(id: number): NotifItem {
  return {
    id,
    type: "order_created",
    title: `t${id}`,
    body: "b",
    data: {},
    created_at: "2026-10-24T00:00:00Z",
    read_at: null,
  };
}

async function freshStore() {
  vi.resetModules();
  const mod = (await import("../notifications")) as unknown as NotifApi;
  return mod.useNotifications();
}

beforeEach(() => {
  vi.mocked(api.patch).mockReset().mockResolvedValue(undefined);
});

afterEach(() => {
  vi.useRealTimers();
});

describe("markRead badge math", () => {
  it("decrements the unread count for an unread item", async () => {
    const store = await freshStore();
    store.unreadCount.value = 3;
    const item = unread(1);

    await store.markRead(item);

    expect(store.unreadCount.value).toBe(2);
    expect(item.read_at).not.toBeNull();
  });

  it("does not decrement for an already-read item", async () => {
    const store = await freshStore();
    store.unreadCount.value = 1;
    const item = { ...unread(1), read_at: "2026-10-24T01:00:00Z" };

    await store.markRead(item);

    expect(store.unreadCount.value).toBe(1);
    expect(api.patch).not.toHaveBeenCalled();
  });

  it("never drops below zero", async () => {
    const store = await freshStore();
    store.unreadCount.value = 0;

    await store.markRead(unread(9));

    expect(store.unreadCount.value).toBe(0);
  });
});

describe("markAllRead", () => {
  it("zeros the badge and stamps every item", async () => {
    const store = await freshStore();
    store.unreadCount.value = 4;
    store.items.value = [unread(1), unread(2), { ...unread(3), read_at: "x" }];

    await store.markAllRead();

    expect(store.unreadCount.value).toBe(0);
    expect(store.items.value.every((item) => item.read_at !== null)).toBe(true);
  });
});
