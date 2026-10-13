// 統一的 API client：
// - 所有請求走 /api 前綴（Vite dev proxy / nginx 正式環境轉發到 FastAPI）
// - credentials: "include" 讓瀏覽器自動帶 session cookie
// - 錯誤統一包成 ApiError（帶 HTTP status），呼叫端用 status 分流處理

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const hasBody = options.body !== undefined;

  const response = await fetch(`/api${path}`, {
    credentials: "include",
    headers: hasBody ? { "Content-Type": "application/json" } : undefined,
    ...options,
  });

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

  return (await response.json()) as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: "POST",
      body: body === undefined ? undefined : JSON.stringify(body),
    }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
};
