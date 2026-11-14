import { createApp } from "vue";

import App from "./App.vue";
import router from "./router";
import "./assets/tailwind.css";
import "./assets/design.css";

// 訪客報到：SPA 成功啟動 = 訪客（v2.6）。fire-and-forget——統計
// 不該影響任何 UX，失敗靜默（圖床事故教訓：外部相依不擋主流程）。
void fetch("/api/visitors/track", { method: "POST" }).catch(() => {});

createApp(App).use(router).mount("#app");
