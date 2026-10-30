-- e2e 商品 seed：內容的唯一來源。由 setup project（tests/auth.setup.ts）讀入執行，
-- 本地與 CI 都走同一條路徑——CI workflow 不再另外注入，也沒有 npm script 版本。
-- 冪等（名稱防呆），重複執行不會產生第二份。
--
-- 這兩個商品是測試的契約：A（$10、庫存 50）可下單，B（$20、庫存 0）缺貨對照。
-- 排序旅程依賴 A < B 的價格關係——改這裡的數字前先看誰在依賴它。

INSERT INTO products (name, description, price, stock, is_active)
SELECT 'E2E Widget A', 'Seeded product for e2e journeys', 10.00, 50, true
WHERE NOT EXISTS (SELECT 1 FROM products WHERE name = 'E2E Widget A');

INSERT INTO products (name, description, price, stock, is_active)
SELECT 'E2E Widget B', 'Seeded product for e2e journeys', 20.00, 0, true
WHERE NOT EXISTS (SELECT 1 FROM products WHERE name = 'E2E Widget B');
