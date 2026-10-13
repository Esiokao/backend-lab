import { ref } from "vue";

// 全域 toast 通知（ShellLayout 負責渲染）。
const message = ref("");
let timer: number | undefined;

export function useToast() {
  function show(text: string, duration = 3000): void {
    message.value = text;

    if (timer !== undefined) window.clearTimeout(timer);
    timer = window.setTimeout(() => {
      message.value = "";
    }, duration);
  }

  function dismiss(): void {
    message.value = "";
  }

  return { message, show, dismiss };
}
