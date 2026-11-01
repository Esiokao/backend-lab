<script setup lang="ts">
// 根元件：路由出口 + 全域 toast outlet（放在這裡讓 toast 跨版面存活——
// 例如改密碼成功後強制跳轉登入頁，提示不會被版面卸載吃掉）。
import { useFaviconBadge } from "@/lib/favicon-badge";
import { useToast } from "@/stores/toast";
import Icon from "@/components/Icon.vue";

const { message, dismiss } = useToast();

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
