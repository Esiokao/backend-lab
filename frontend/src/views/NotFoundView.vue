<script setup lang="ts">
import StorefrontFooter from "@/components/StorefrontFooter.vue";
import StorefrontHeader from "@/components/StorefrontHeader.vue";

// 404 Not Found（全域 catch-all）：未知路由不再靜默回首頁，
// 給使用者明確狀態與出口。样式沿用結帳結果頁的 token 設計系統。
</script>

<template>
  <StorefrontHeader />

  <main class="storefront-main">
    <section class="notfound-hero" role="status">
      <span class="notfound-code">404</span>
      <h1>Page not found</h1>
      <p>
        This page doesn't exist — it may have been moved, or the address is mistyped.
        Your data is safe; nothing was lost.
      </p>
      <div class="notfound-actions">
        <router-link class="primary-button" :to="{ name: 'storefront' }">
          Back to storefront
        </router-link>
        <router-link class="ghost-button" :to="{ name: 'about' }">
          About this project
        </router-link>
      </div>
    </section>
  </main>

  <StorefrontFooter />
</template>

<style scoped>
.notfound-hero {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  margin: 40px auto 0;
  max-width: 560px;
  padding: 48px 40px;
  border: 1.5px solid var(--line-strong);
  border-radius: 14px;
  background: var(--card);
  box-shadow: var(--shadow-card);
  animation: rise-in 0.4s ease backwards;
}

.notfound-code {
  font-family: var(--font-mono);
  font-size: 56px;
  font-weight: 700;
  line-height: 1;
  letter-spacing: 0.08em;
  color: var(--ink-faint);
}

.notfound-hero h1 {
  margin: 12px 0 0;
  font-size: 24px;
  font-weight: 700;
  color: var(--ink-strong);
}

.notfound-hero p {
  margin: 0;
  max-width: 42ch;
  font-size: 13px;
  line-height: 1.6;
  color: var(--ink-soft);
}

.notfound-actions {
  margin-top: 18px;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: center;
}
</style>
