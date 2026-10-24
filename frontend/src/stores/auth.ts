import { ref } from "vue";

import { api } from "@/lib/api";
import { CurrentUserSchema, type CurrentUser } from "@/lib/schemas";

// 極簡 auth 狀態（模組級 ref，整個 app 共享）。
// 之後如果狀態變複雜再考慮 Pinia。
const user = ref<CurrentUser | null>(null);
const loaded = ref(false);

export function useAuth() {
  // GET /users/me 探測登入狀態；401 視為未登入。
  async function me(): Promise<CurrentUser | null> {
    try {
      user.value = await api.get("/users/me", CurrentUserSchema);
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

  // 會員資料修改後同步整個 app 共享的使用者狀態（側欄、下拉選單即時更新）。
  function setUser(next: CurrentUser): void {
    user.value = next;
  }

  return { user, loaded, me, login, logout, setUser };
}
