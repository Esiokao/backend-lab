<script setup lang="ts">
// 根元件：路由出口 + 全域 toast outlet（放在這裡讓 toast 跨版面存活——
// 例如改密碼成功後強制跳轉登入頁，提示不會被版面卸載吃掉）。
import { onMounted, onUnmounted, watch } from "vue";

import { useFaviconBadge } from "@/lib/favicon-badge";
import { useAuth } from "@/stores/auth";
import { useNotifications } from "@/stores/notifications";
import { useToast } from "@/stores/toast";
import Icon from "@/components/Icon.vue";

const { message, dismiss } = useToast();
const { user } = useAuth();
const { startPolling, stopPolling } = useNotifications();

// 通知輪詢/SSE 的生命週期掛在根元件、跟著登入狀態走：
// 未登入不發請求；登入後跨頁存活——店面停留時 favicon 紅點也即時更新
// （原本掛在 NotificationCenter，元件卸載就斷線，店面會脫隊）。
onMounted(() => {
  if (user.value) startPolling();
});
watch(user, (value) => {
  if (value) startPolling();
  else stopPolling();
});
onUnmounted(() => stopPolling());

// 有未讀通知時，分頁 icon 疊紅點（追蹤 notifications store 的未讀數）
useFaviconBadge();
</script>

<template>
  <router-view />

  <Transition name="toast">
    <div v-if="message" class="toast" role="status">
      <span><Icon name="shield" :size="17" /></span>{{ message }}
      <button type="button" aria-label="Dismiss notification" @click="dismiss">
        <Icon name="close" :size="15" />
      </button>
    </div>
  </Transition>
</template>
