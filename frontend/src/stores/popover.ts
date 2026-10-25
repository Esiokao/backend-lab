import { ref } from "vue";

// Popover 互斥（v1.10）：同一時間只開一個浮層（通知面板 / 帳號選單）。
// 開新的 → 舊的自動收：解決右側同位的兩個浮層疊在一起（穿模）。

const active = ref<string | null>(null);

function openPopover(name: string): void {
  active.value = name;
}

function closePopover(name: string): void {
  if (active.value === name) active.value = null;
}

export function usePopover() {
  return { active, openPopover, closePopover };
}

// Esc 關閉任何浮層（通知面板 / 帳號選單）：store 是浮層狀態的唯一真相，全域掛一次即可。
// 產品 modal 有自己的 Esc handler（僅 admin），兩者互不干擾。
function onEscKeydown(event: KeyboardEvent): void {
  if (event.key === "Escape") active.value = null;
}

if (typeof window !== "undefined") {
  window.addEventListener("keydown", onEscKeydown);
}
