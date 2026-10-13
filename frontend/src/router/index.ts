import { createRouter, createWebHistory } from "vue-router";

import { useAuth } from "@/stores/auth";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/login",
      name: "login",
      component: () => import("@/views/LoginView.vue"),
      meta: { guestOnly: true },
    },
    {
      path: "/",
      component: () => import("@/layouts/ShellLayout.vue"),
      meta: { requiresAuth: true },
      children: [
        { path: "", name: "dashboard", component: () => import("@/views/DashboardView.vue") },
        { path: "orders", name: "orders", component: () => import("@/views/OrdersView.vue") },
        { path: "users", name: "users", component: () => import("@/views/UsersView.vue") },
        {
          path: "api-health",
          name: "api-health",
          component: () => import("@/views/ApiHealthView.vue"),
        },
      ],
    },
    { path: "/:pathMatch(.*)*", redirect: "/" },
  ],
});

// 全域登入守衛：
// - requiresAuth：未登入 → 踢到 /login（帶 redirect 參數，登入後回原頁）
// - guestOnly：已登入還去 /login → 送回儀表板
router.beforeEach(async (to) => {
  const { me, user, loaded } = useAuth();

  if (!loaded.value) await me();

  if (to.meta.requiresAuth && !user.value) {
    return { name: "login", query: { redirect: to.fullPath } };
  }

  if (to.meta.guestOnly && user.value) {
    return { name: "dashboard" };
  }
});

export default router;
