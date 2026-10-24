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
      // 購物車（v1.7）：店面購物流的一環，不住在會員後台；
      // 訪客可開頁，由頁面引導登入（車存在後端，屬於登入者）。
      path: "/cart",
      name: "cart",
      component: () => import("@/views/CartView.vue"),
    },
    {
      // 登入後應用區（v1.4 自 / 前綴遷入）。
      // 原 /app/users 已移除：後端 GET /users 為 admin-only（repo 為準），
      // 使用者管理歸 /admin/users。
      path: "/app",
      component: () => import("@/layouts/ShellLayout.vue"),
      meta: { requiresAuth: true },
      children: [
        { path: "", redirect: { name: "dashboard" } },
        {
          // 系統監控儀表板屬 workspace：僅 admin（一般使用者走會員中心 /app/account）。
          path: "dashboard",
          name: "dashboard",
          component: () => import("@/views/DashboardView.vue"),
          meta: { requiresAdmin: true },
        },
        { path: "orders", name: "orders", component: () => import("@/views/OrdersView.vue") },
        {
          // 訂單詳情（後端允許擁有者或 admin 讀取）。
          path: "orders/:id",
          name: "order-detail",
          component: () => import("@/views/OrderDetailView.vue"),
        },
        {
          // 會員中心：會員資料修改 + 修改密碼（F7）。
          path: "account",
          name: "account",
          component: () => import("@/views/AccountView.vue"),
        },
        {
          path: "api-health",
          name: "api-health",
          component: () => import("@/views/ApiHealthView.vue"),
          meta: { requiresAdmin: true },
        },
      ],
    },
    {
      // Admin 管理區（F8/F9/F10）。
      path: "/admin",
      component: () => import("@/layouts/ShellLayout.vue"),
      meta: { requiresAuth: true, requiresAdmin: true },
      children: [
        { path: "", redirect: { name: "admin-orders" } },
        {
          path: "orders",
          name: "admin-orders",
          component: () => import("@/views/AdminOrdersView.vue"),
        },
        {
          path: "users",
          name: "admin-users",
          component: () => import("@/views/AdminUsersView.vue"),
        },
        {
          // 分類管理（v1.6：/categories CRUD）。
          path: "categories",
          name: "admin-categories",
          component: () => import("@/views/AdminCategoriesView.vue"),
        },
        {
          // 使用者詳情（GET /admin/users/{id}：基本資料 + 訂單）。
          path: "users/:id",
          name: "admin-user-detail",
          component: () => import("@/views/AdminUserDetailView.vue"),
        },
        {
          // 通知管理：定向發送 + 廣播（F11 admin UI）。
          path: "notifications",
          name: "admin-notifications",
          component: () => import("@/views/AdminNotificationsView.vue"),
        },
      ],
    },
    // 舊路徑（/orders、/users、/api-health、/app/users）與未知路徑一律回店面。
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

  // 角色化守衛（F10-2）：非 admin 試圖進入 admin 專屬頁 → 導回會員中心
  // （不能導回 dashboard：它現在本身也是 admin 專屬，會造成循環）。
  if (to.meta.requiresAdmin && user.value?.role !== "admin") {
    return { name: "account" };
  }

  if (to.meta.guestOnly && user.value) {
    return { path: "/" };
  }
});

export default router;
