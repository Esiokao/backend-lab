// Favicon 小紅點（F11 補充）：有未讀通知時，在分頁圖示上疊一顆紅點。
//
// 原理：canvas 把 base favicon（像素貓）畫到 64×64、右上角疊紅點，
// 產出 data URL 寫回 <link rel="icon"> 的 href。unreadCount 變化時重畫。
//
// 為什麼用 canvas 而不是預先做兩張圖：點的位置/大小跟著 base 圖走，
// 將來換 favicon 不用重畫圖；數字版（99+）之後要加也只是多一段繪製。

import { watch } from "vue";

import { useNotifications } from "@/stores/notifications";

const BASE_FAVICON = "/brand-cat.png";
const DOT_COLOR = "#e5484d";
const RING_COLOR = "#ffffff";
const SIZE = 64;

function applyFavicon(href: string): void {
  // index.html 的 <link rel="icon">；SPA 生命週期中只有一份，找不到就算了（SSR/測試環境）。
  const link = document.querySelector<HTMLLinkElement>('link[rel="icon"]');
  if (link) link.href = href;
}

function drawBadge(unread: number): void {
  if (unread <= 0) {
    applyFavicon(BASE_FAVICON);
    return;
  }

  const img = new Image();
  img.onload = () => {
    const canvas = document.createElement("canvas");
    canvas.width = SIZE;
    canvas.height = SIZE;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // 像素貓放大：關掉平滑取樣，保持俐落的像素邊緣
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(img, 0, 0, SIZE, SIZE);

    // 右上角紅點 + 白圈（在深淺底都看得清）
    const radius = SIZE * 0.26;
    const cx = SIZE - radius - 2;
    const cy = radius + 2;
    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    ctx.fillStyle = DOT_COLOR;
    ctx.fill();
    ctx.lineWidth = SIZE * 0.06;
    ctx.strokeStyle = RING_COLOR;
    ctx.stroke();

    applyFavicon(canvas.toDataURL("image/png"));
  };
  // 圖載入完成才畫（Image 載入是非同步的）
  img.src = BASE_FAVICON;
}

export function useFaviconBadge(): void {
  const { unreadCount, broadcastsUnread } = useNotifications();

  // 鈴鐺 badge 用同一組數字當真相來源：SSE/輪詢更新 store → 這裡自動跟上
  watch(
    () => unreadCount.value + broadcastsUnread.value,
    (total) => drawBadge(total),
    { immediate: true },
  );
}
