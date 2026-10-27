<script setup lang="ts">
import Icon from "@/components/Icon.vue";

// 店面頁尾（v1.18）：圖紙 colophon —— 公開頁面在每頁有收尾，
// 不再「最後一張卡之後就斷」；連結收回站點三個主要目的地。
</script>

<template>
  <footer class="storefront-footer">
    <div class="footer-inner">
      <router-link class="footer-brand" :to="{ name: 'storefront' }">
        <span class="brand-mark"><Icon name="bolt" :size="13" /></span>
        Backend Lab
      </router-link>
      <nav class="footer-nav" aria-label="Footer">
        <router-link :to="{ name: 'storefront' }">Store</router-link>
        <router-link :to="{ name: 'cart' }">Cart</router-link>
        <router-link :to="{ name: 'about' }">About us</router-link>
      </nav>
      <span class="footer-colophon">Sheet 01 · Backend Lab · drawn 2026</span>
    </div>
  </footer>
</template>
