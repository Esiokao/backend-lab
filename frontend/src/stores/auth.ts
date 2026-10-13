import { ref } from "vue";

import { api } from "@/lib/api";

// 極簡 auth 狀態（模組級 ref，整個 app 共享）。
// 之後如果狀態變複雜再考慮 Pinia。
export type CurrentUser = { id: number; name: string; email: string };

const user = ref<CurrentUser | null>(null);
const loaded = ref(false);

export function useAuth() {
  // GET /users/me 探測登入狀態；401 視為未登入。
  async function me(): Promise<CurrentUser | null> {
    try {
      user.value = await api.get<CurrentUser>("/users/me");
    } catch {
      user.value = null;
    }
    loaded.value = true;
    return user.value;
  }

  async function login(email: string, password: string): Promise<void> {
    // 成功時 Set-Cookie 由瀏覽器自動保管，前端不碰任何 token。
    await api.post("/login", { email, password });
    await me();
  }

  async function logout(): Promise<void> {
    try {
      await api.post("/logout");
    } finally {
      user.value = null;
    }
  }

  return { user, loaded, me, login, logout };
}
