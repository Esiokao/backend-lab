import { createRouter, createWebHistory } from "vue-router";

import { useAuth } from "@/stores/auth";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      // v1.4：公開商品店面，訪客可逛，守衛不攔截（F12-7）。
      path: "/",
      name: "storefront",
      component: () => import("@/views/StorefrontView.vue"),
    },
    {
      path: "/login",
      name: "login",
      component: () => import("@/views/LoginView.vue"),
      meta: { guestOnly: true },
    },
    {
      // 登入後應用區（v1.4 自 / 前綴遷入）。
      path: "/app",
      component: () => import("@/layouts/ShellLayout.vue"),
      meta: { requiresAuth: true },
      children: [
        { path: "", redirect: { name: "dashboard" } },
        {
          path: "dashboard",
          name: "dashboard",
          component: () => import("@/views/DashboardView.vue"),
        },
        { path: "orders", name: "orders", component: () => import("@/views/OrdersView.vue") },
        { path: "users", name: "users", component: () => import("@/views/UsersView.vue") },
        {
          path: "api-health",
          name: "api-health",
          component: () => import("@/views/ApiHealthView.vue"),
        },
      ],
    },
    // 舊路徑（/orders、/users、/api-health）與未知路徑一律回店面（已核可，不保留相容）。
    { path: "/:pathMatch(.*)*", redirect: "/" },
  ],
});

// 全域登入守衛：
// - `/`（店面）公開，不攔截
// - requiresAuth：未登入 → 踢到 /login（帶 redirect 參數，登入後回原頁）
// - guestOnly：已登入還去 /login → 送回店面（F2-5）
router.beforeEach(async (to) => {
  const { me, user, loaded } = useAuth();

  if (!loaded.value) await me();

  if (to.meta.requiresAuth && !user.value) {
    return { name: "login", query: { redirect: to.fullPath } };
  }

  if (to.meta.guestOnly && user.value) {
    return { path: "/" };
  }
});

export default router;
