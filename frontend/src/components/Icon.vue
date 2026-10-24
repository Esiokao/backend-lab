<script setup lang="ts">
// 內嵌 SVG 圖示（移植自設計模板，14 顆線性圖示）。
export type IconName =
  | "activity"
  | "moon"
  | "sun"
  | "arrow"
  | "bell"
  | "bolt"
  | "cart"
  | "box"
  | "chevron"
  | "close"
  | "database"
  | "grid"
  | "logout"
  | "plus"
  | "search"
  | "server"
  | "shield"
  | "star"
  | "users";

const props = withDefaults(defineProps<{ name: IconName; size?: number }>(), {
  size: 18,
});

const iconPaths: Record<IconName, string[]> = {
  activity: ["M3 12h4l2.2-6 4.1 12 2.1-6H21"],
  moon: ["M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z"],
  sun: ["M12 3v2M12 19v2M5 12H3M21 12h-2M6.3 6.3 4.9 4.9M19.1 19.1l-1.4-1.4M17.7 6.3l1.4-1.4M4.9 19.1l1.4-1.4", "M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z"],
  arrow: ["m9 18 6-6-6-6"],
  bell: ["M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9", "M13.73 21a2 2 0 0 1-3.46 0"],
  bolt: ["m13 2-8 12h7l-1 8 8-12h-7l1-8Z"],
  cart: ["M2.05 2.05h2l2.66 12.42a2 2 0 0 0 2 1.58h9.78a2 2 0 0 0 1.95-1.57l1.65-7.43H5.12", "M8 21h.01", "M19 21h.01"],
  box: ["m4 7 8-4 8 4-8 4-8-4Z", "m4 7 8 4 8-4M4 7v10l8 4 8-4V7M12 11v10"],
  chevron: ["m8 10 4 4 4-4"],
  close: ["m6 6 12 12M18 6 6 18"],
  database: [
    "M4 5c0-1.7 3.6-3 8-3s8 1.3 8 3-3.6 3-8 3-8-1.3-8-3Z",
    "M4 5v7c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 12v7c0 1.7 3.6 3 8 3s8-1.3 8-3v-7",
  ],
  grid: ["M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z"],
  logout: ["M10 17l5-5-5-5M15 12H3M15 4h4a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-4"],
  plus: ["M12 5v14M5 12h14"],
  search: ["m21 21-4.4-4.4M19 11a8 8 0 1 1-16 0 8 8 0 0 1 16 0Z"],
  server: [
    "M5 4h14a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2ZM5 14h14a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-2a2 2 0 0 1 2-2ZM7 7h.01M7 17h.01",
  ],
  shield: ["M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Zm-3-10 2 2 4-4"],
  star: [
    "M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z",
  ],
  users: [
    "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM22 21v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8",
  ],
};
</script>

<template>
  <svg
    :viewBox="'0 0 24 24'"
    :width="props.size"
    :height="props.size"
    fill="none"
    stroke="currentColor"
    stroke-width="1.8"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <path v-for="(d, index) in iconPaths[props.name]" :key="index" :d="d" />
  </svg>
</template>
