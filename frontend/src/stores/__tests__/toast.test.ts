import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// toast store：3 秒自動消失與手動 dismiss。

type ToastApi = {
  useToast: () => {
    message: { value: string };
    show: (message: string) => void;
    dismiss: () => void;
  };
};

async function freshToast() {
  vi.resetModules();
  const mod = (await import("../toast")) as unknown as ToastApi;
  return mod.useToast();
}

beforeEach(() => {
  // store 使用 window.setTimeout；node 環境以 globalThis 代打（fake timers 會接管）。
  vi.stubGlobal("window", globalThis);
  vi.useFakeTimers();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("toast store", () => {
  it("shows the message immediately", async () => {
    const toast = await freshToast();
    toast.show("Saved.");
    expect(toast.message.value).toBe("Saved.");
  });

  it("auto-dismisses after 3 seconds", async () => {
    const toast = await freshToast();
    toast.show("Saved.");

    vi.advanceTimersByTime(2999);
    expect(toast.message.value).toBe("Saved.");

    vi.advanceTimersByTime(1);
    expect(toast.message.value).toBe("");
  });

  it("dismiss clears the message early", async () => {
    const toast = await freshToast();
    toast.show("Saved.");

    toast.dismiss();
    expect(toast.message.value).toBe("");
  });

  it("replaces the message and restarts the timer", async () => {
    const toast = await freshToast();
    toast.show("First");

    vi.advanceTimersByTime(2000);
    toast.show("Second");

    vi.advanceTimersByTime(2000); // 距 First 已 4 秒，但 Second 才 2 秒
    expect(toast.message.value).toBe("Second");

    vi.advanceTimersByTime(1000);
    expect(toast.message.value).toBe("");
  });
});
