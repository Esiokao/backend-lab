import { z } from "zod";

// API 契約 schemas（zod）：與後端 Pydantic 對齊的單一真相來源。
// Decimal 後端序列化為字串或數字 → 統一 transform 成 number。
const decimal = z
  .union([z.string(), z.number()])
  .transform((value) => Number(value));

// ── Auth / Users ──
export const CurrentUserSchema = z.object({
  id: z.number().int(),
  name: z.string(),
  email: z.string(),
  role: z.enum(["user", "admin"]),
});
export type CurrentUser = z.infer<typeof CurrentUserSchema>;

// ── Catalog ──
export const CategorySchema = z.object({
  id: z.number().int(),
  name: z.string(),
  description: z.string().nullable(),
});
export type Category = z.infer<typeof CategorySchema>;
export const CategoryListSchema = z.array(CategorySchema);

export const ProductSchema = z.object({
  id: z.number().int(),
  name: z.string(),
  description: z.string().nullable(),
  image_url: z.string().nullable(),
  price: decimal,
  stock: z.number().int(),
  category_id: z.number().int().nullable(),
  created_at: z.string(),
  is_active: z.boolean(),
});
export type Product = z.infer<typeof ProductSchema>;
export const ProductListSchema = z.array(ProductSchema);

// ── Cart ──
export const CartItemSchema = z.object({
  product_id: z.number().int(),
  product_name: z.string(),
  quantity: z.number().int(),
  unit_price: decimal,
  subtotal: decimal,
  stock: z.number().int(),
});
export type CartItem = z.infer<typeof CartItemSchema>;

export const CartSchema = z.object({
  items: z.array(CartItemSchema),
  total: decimal,
});
export type Cart = z.infer<typeof CartSchema>;

// ── Orders ──
export const OrderItemSchema = z.object({
  product_id: z.number().int(),
  quantity: z.number().int(),
  unit_price: decimal,
});
export type OrderItem = z.infer<typeof OrderItemSchema>;

export const OrderSchema = z.object({
  id: z.number().int(),
  user_id: z.number().int(),
  status: z.string(),
  created_at: z.string(),
  items: z.array(OrderItemSchema),
  paid_at: z.string().nullable(),
});
export type Order = z.infer<typeof OrderSchema>;

// ── Notifications ──
export const NotificationItemSchema = z.object({
  id: z.number().int(),
  type: z.string(),
  title: z.string(),
  body: z.string(),
  data: z.record(z.string(), z.unknown()),
  created_at: z.string(),
  read_at: z.string().nullable(),
});
export type NotificationItem = z.infer<typeof NotificationItemSchema>;

export const BroadcastSchema = z.object({
  id: z.number().int(),
  type: z.string(),
  title: z.string(),
  body: z.string(),
  created_at: z.string(),
});
export type Broadcast = z.infer<typeof BroadcastSchema>;

export const UnreadCountSchema = z.object({ unread_count: z.number().int() });

// ── Stats ──
export const StatsSchema = z.object({
  scope: z.enum(["global", "personal"]),
  total_users: z.number().int().optional(),
  total_orders: z.number().int(),
  orders_today: z.number().int(),
  unread_notifications: z.number().int().optional(),
});
export type Stats = z.infer<typeof StatsSchema>;

// ── 表單驗證 schemas（提交前先擋，inline 顯示欄位錯誤）──
export const LoginFormSchema = z.object({
  email: z.email("Enter a valid email address."),
  password: z.string().min(1, "Password is required."),
});

export const SignupFormSchema = z.object({
  name: z.string().trim().min(1, "Name is required."),
  email: z.email("Enter a valid email address."),
  password: z.string().min(8, "Password must be at least 8 characters.").max(128),
});

export const ProfileFormSchema = z.object({
  name: z.string().trim().min(1, "Name is required."),
  email: z.email("Enter a valid email address."),
});

export const PasswordFormSchema = z
  .object({
    next: z
      .string()
      .min(8, "Password must be at least 8 characters.")
      .max(128, "Password must be at most 128 characters."),
    confirm: z.string(),
  })
  .refine((data) => data.next === data.confirm, {
    message: "Passwords do not match.",
    path: ["confirm"],
  });

export const ProductFormSchema = z.object({
  name: z.string().trim().min(1, "Product name is required."),
  description: z.string(),
  image_url: z.string(),
  price: z.coerce
    .number({ message: "Price must be a number." })
    .min(0, "Price must be non-negative."),
  stock: z.coerce
    .number({ message: "Stock must be a number." })
    .int("Stock must be an integer.")
    .min(0, "Stock must be non-negative."),
});
