-- 清理目標：本地 dev DB（backend_lab）。CI 的 DB 即焚，不需要清理。
\connect backend_lab

-- 清理 e2e 測試帳號及其殘留資料。
-- 只刪 e2e 專屬 email（%@e2e.example.com），且跳過有訂單的帳號
-- （orders 沒有 cascade，避免誤刪；e2e 旅程本來就不會下訂單）。
-- cart_items / product_follows 有 ON DELETE CASCADE，會跟著 users 一起消失。

DELETE FROM notifications
WHERE user_id IN (SELECT id FROM users WHERE email LIKE '%@e2e.example.com');

DELETE FROM users
WHERE email LIKE '%@e2e.example.com'
  AND id NOT IN (SELECT DISTINCT user_id FROM orders);
