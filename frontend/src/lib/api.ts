// 統一的 API client：
// - 所有請求走 /api 前綴（Vite dev proxy / nginx 正式環境轉發到 FastAPI）
// - credentials: "include" 讓瀏覽器自動帶 session cookie
// - 錯誤統一包成 ApiError（帶 HTTP status），呼叫端用 status 分流處理
// - 帶 schema（zod）時回應先驗契約：不合就丟 SchemaError（後端改壞契約會當場炸，
//   不會默默拿到錯的資料）

import type { z } from "zod";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export class SchemaError extends Error {
  issues: string;

  constructor(issues: string) {
    super(`Invalid API response: ${issues}`);
    this.issues = issues;
  }
}

function parseWith<T>(schema: z.ZodType<T> | undefined, data: unknown): T {
  if (schema === undefined) return data as T;

  const result = schema.safeParse(data);
  if (!result.success) {
    throw new SchemaError(
      result.error.issues
        .map((issue) => `${issue.path.join(".") || "(root)"}: ${issue.message}`)
        .join("; "),
    );
  }
  return result.data;
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  schema?: z.ZodType<T>,
): Promise<T> {
  const hasBody = options.body !== undefined;

  const response = await fetch(`/api${path}`, {
    credentials: "include",
    headers: hasBody ? { "Content-Type": "application/json" } : undefined,
    ...options,
  });

  if (response.status === 204) return undefined as T;

  if (!response.ok) {
    let detail = response.statusText;

    try {
      const body = (await response.json()) as { detail?: string };
      if (body?.detail) detail = body.detail;
    } catch {
      // 回應不是 JSON 就用 statusText。
    }

    throw new ApiError(response.status, detail);
  }

  return parseWith(schema, await response.json());
}

export const api = {
  get: <T>(path: string, schema?: z.ZodType<T>) => request<T>(path, {}, schema),
  post: <T>(path: string, body?: unknown, schema?: z.ZodType<T>) =>
    request<T>(
      path,
      {
        method: "POST",
        body: body === undefined ? undefined : JSON.stringify(body),
      },
      schema,
    ),
  patch: <T>(path: string, body: unknown, schema?: z.ZodType<T>) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(body) }, schema),
  delete: <T>(path: string, schema?: z.ZodType<T>) =>
    request<T>(path, { method: "DELETE" }, schema),
};
