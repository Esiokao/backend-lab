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
      meta: { title: "Storefront" },
    },
    {
      path: "/login",
      name: "login",
      component: () => import("@/views/LoginView.vue"),
      meta: { guestOnly: true, title: "Sign in" },
    },
    {
      // 購物車（v1.7）：店面購物流的一環，不住在會員後台；
      // 訪客可開頁，由頁面引導登入（車存在後端，屬於登入者）。
      path: "/cart",
      name: "cart",
      component: () => import("@/views/CartView.vue"),
      meta: { title: "Cart" },
    },
    {
      // 結帳/付款頁（v1.8）：選中明細 → Pay → 結果頁。
      path: "/checkout",
      name: "checkout",
      component: () => import("@/views/CheckoutView.vue"),
      meta: { title: "Checkout" },
    },
    {
      // 結帳結果頁：完成 / 失敗（失敗可回訂單重試 Pay now）。
      path: "/checkout/result",
      name: "checkout-result",
      component: () => import("@/views/CheckoutResultView.vue"),
      meta: { title: "Checkout result" },
    },
    {
      // 商品詳情頁（v1.18）：公開；店面卡片圖片與名稱連入（修「商品卡是死路」）。
      path: "/product/:id",
      name: "product-detail",
      component: () => import("@/views/ProductDetailView.vue"),
      meta: { title: "Product" },
    },
    {
      // About us：repo 的 tech stack（公開）。
      path: "/about",
      name: "about",
      component: () => import("@/views/AboutView.vue"),
      meta: { title: "About us" },
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
          meta: { requiresAdmin: true, title: "Overview" },
        },
        {
          path: "orders",
          name: "orders",
          component: () => import("@/views/OrdersView.vue"),
          meta: { title: "My orders" },
        },
        {
          // 訂單詳情（後端允許擁有者或 admin 讀取）。
          path: "orders/:id",
          name: "order-detail",
          component: () => import("@/views/OrderDetailView.vue"),
      meta: { title: "Order detail" },
        },
        {
          // 會員中心（v1.9）：唯讀資料頁 + 編輯區分離。
          path: "account",
          name: "account",
          component: () => import("@/views/AccountView.vue"),
      meta: { title: "My account" },
        },
        {
          // 會員資料編輯：資料修改 + 改密碼（F7）。
          path: "account/edit",
          name: "account-edit",
          component: () => import("@/views/AccountEditView.vue"),
      meta: { title: "Edit profile" },
        },
        {
          path: "api-health",
          name: "api-health",
          component: () => import("@/views/ApiHealthView.vue"),
          meta: { requiresAdmin: true, title: "API Health" },
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
      meta: { title: "Order Management" },
        },
        {
          path: "users",
          name: "admin-users",
          component: () => import("@/views/AdminUsersView.vue"),
      meta: { title: "User Management" },
        },
        {
          // 分類管理（v1.6：/categories CRUD）。
          path: "categories",
          name: "admin-categories",
          component: () => import("@/views/AdminCategoriesView.vue"),
      meta: { title: "Category Management" },
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
      meta: { title: "Notifications" },
        },
      ],
    },
    // 舊路徑保留明確 redirect（/orders、/users、/api-health、/app/users），
    // 讓舊書籤仍能到家；其餘未知路徑才落到 404 頁。
    { path: "/orders", redirect: { name: "orders" } },
    { path: "/users", redirect: { name: "admin-users" } },
    { path: "/api-health", redirect: { name: "api-health" } },
    { path: "/app/users", redirect: { name: "admin-users" } },
    {
      // 全域 404：未知路由顯示 Not Found 頁，不再靜默回首頁。
      path: "/:pathMatch(.*)*",
      name: "not-found",
      component: () => import("@/views/NotFoundView.vue"),
      meta: { title: "Not found" },
    },
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

  // 分頁標題反映所在位置；店面（動態分類）由 StorefrontView 覆寫。
  const title = to.meta.title as string | undefined;
  if (title) document.title = `${title} · Backend Lab`;
});

export default router;
