import { ref } from "vue";

// 佈景主題（v1.5 dark mode）：light = pinned 奶油世界；dark = 暖炭黑夜間版。
// localStorage 持久化；index.html 內嵌腳本在啟動前先套 data-theme，避免閃白。
export type Theme = "light" | "dark";

const STORAGE_KEY = "bl-theme";

const theme = ref<Theme>(
  (typeof localStorage !== "undefined" && localStorage.getItem(STORAGE_KEY) === "dark"
    ? "dark"
    : "light") as Theme,
);

function apply(): void {
  document.documentElement.dataset.theme = theme.value;
}

function setTheme(next: Theme): void {
  theme.value = next;
  localStorage.setItem(STORAGE_KEY, next);
  apply();
}

function toggleTheme(): void {
  setTheme(theme.value === "light" ? "dark" : "light");
}

apply();

export function useTheme() {
  return { theme, setTheme, toggleTheme };
}
