import { ref } from "vue";

import { api } from "@/lib/api";
import { FollowedSchema } from "@/lib/schemas";
import { useAuth } from "@/stores/auth";

// 商品收藏 store：對接 /products/{id}/follow（POST/DELETE）與 /products/followed（ids）。
// 單例狀態 + 登入者 mount 時 load——修復「重整後星星熄滅」
// （舊版兩個 view 各自 local ref、初始化 false，重整即失憶）。
const followedIds = ref<Set<number>>(new Set());
const loaded = ref(false);

const isFollowed = (productId: number) => followedIds.value.has(productId);

async function load(): Promise<void> {
  const { user } = useAuth();
  // guest 沒有收藏可言：直接清空，不打 API。
  if (!user.value) {
    followedIds.value = new Set();
    loaded.value = true;
    return;
  }
  try {
    const data = await api.get("/products/followed", FollowedSchema);
    followedIds.value = new Set(data.product_ids);
  } catch {
    // 401（session 過期）或暫時失敗：保持空狀態，星星可再按。
  } finally {
    loaded.value = true;
  }
}

// 樂觀切換：先改本地 Set，摹後同步；失敗回滾並 rethrow 給呼叫方 toast。
async function toggle(productId: number): Promise<boolean> {
  const wasFollowed = followedIds.value.has(productId);
  const next = new Set(followedIds.value);
  if (wasFollowed) next.delete(productId);
  else next.add(productId);
  followedIds.value = next;

  try {
    if (wasFollowed) await api.delete(`/products/${productId}/follow`);
    else await api.post(`/products/${productId}/follow`);
    return !wasFollowed;
  } catch (err) {
    followedIds.value = new Set(followedIds.value); // 回滾到前一狀態
    throw err;
  }
}

// 登出時清空：收藏屬於登入者，星星不該殘留給下一位使用者。
function reset(): void {
  followedIds.value = new Set();
  loaded.value = false;
}

export function useFollows() {
  return { followedIds, loaded, isFollowed, load, toggle, reset };
}
