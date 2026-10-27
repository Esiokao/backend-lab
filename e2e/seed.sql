-- e2e 商品 seed：CI 的 DB 是全新的，店面必須至少有在庫商品，
-- store 旅程才找得到「Add to cart」。本地跑也不會重複（名稱防呆）。

INSERT INTO products (name, description, price, stock, is_active)
SELECT 'E2E Widget A', 'Seeded product for e2e journeys', 10.00, 50, true
WHERE NOT EXISTS (SELECT 1 FROM products WHERE name = 'E2E Widget A');

INSERT INTO products (name, description, price, stock, is_active)
SELECT 'E2E Widget B', 'Seeded product for e2e journeys', 20.00, 0, true
WHERE NOT EXISTS (SELECT 1 FROM products WHERE name = 'E2E Widget B');
