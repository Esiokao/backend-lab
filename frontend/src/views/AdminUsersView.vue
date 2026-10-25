<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";

import Icon from "@/components/Icon.vue";
import { ApiError, api } from "@/lib/api";
import { ProfileFormSchema } from "@/lib/schemas";
import { useAuth } from "@/stores/auth";
import { useToast } from "@/stores/toast";

// Admin 使用者管理（F9）。後端契約（以 repo 為準）：
// - GET /users（admin-only）→ UserResponse[]（含 role）
// - PATCH /admin/users/{id}（name/email/role；改自己的 role → 400；email 衝突 → 409）
// - 後端尚無 DELETE /admin/users/{id} 與 GET /admin/users/{id} → 刪除與詳情功能待後端補（記帳中）
// v1.19：編輯改走 Modal（與商品 modal 同語彙），取代表格內 inline row-edit。

type UserRow = { id: number; name: string; email: string; role: "user" | "admin" };

const { user: currentUser } = useAuth();
const toast = useToast();

const users = ref<UserRow[]>([]);
const loading = ref(true);
const loadError = ref("");

// 編輯 Modal：editingUser 非 null = 開啟。
const editingUser = ref<UserRow | null>(null);
const userForm = ref({ name: "", email: "", role: "user" as "user" | "admin" });
const userErrors = ref<Record<string, string>>({});
const busy = ref(false);

const isSelf = computed(() =>
  editingUser.value === null ? false : currentUser.value?.id === editingUser.value.id,
);

async function loadUsers(): Promise<void> {
  loading.value = true;
  loadError.value = "";

  try {
    users.value = await api.get<UserRow[]>("/users");
  } catch (err) {
    loadError.value =
      err instanceof ApiError ? `Failed to load users: ${err.message}` : "Failed to load users.";
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  void loadUsers();
  document.addEventListener("keydown", onModalKeydown);
});

onUnmounted(() => {
  document.removeEventListener("keydown", onModalKeydown);
});

// 名字取前兩字做頭像縮寫。
function initials(name: string): string {
  return name.trim().slice(0, 2).toUpperCase();
}

function openEditModal(user: UserRow): void {
  editingUser.value = user;
  userForm.value = { name: user.name, email: user.email, role: user.role };
  userErrors.value = {};
}

function closeEditModal(): void {
  editingUser.value = null;
  userErrors.value = {};
}

function onModalKeydown(event: KeyboardEvent): void {
  if (event.key === "Escape" && editingUser.value !== null) closeEditModal();
}

async function saveEdit(): Promise<void> {
  const target = editingUser.value;
  if (target === null) return;

  const parsed = ProfileFormSchema.safeParse({
    name: userForm.value.name,
    email: userForm.value.email,
  });
  if (!parsed.success) {
    userErrors.value = Object.fromEntries(
      parsed.error.issues.map((issue) => [String(issue.path[0] ?? ""), issue.message]),
    );
    return;
  }

  // 編輯自己時不送 role 欄位：後端會回 400（不能改自己的 role）。
  const payload: { name: string; email: string; role?: "user" | "admin" } = {
    name: parsed.data.name,
    email: parsed.data.email,
  };
  if (!isSelf.value) payload.role = userForm.value.role;

  busy.value = true;
  try {
    const updated = await api.patch<UserRow>(`/admin/users/${target.id}`, payload);

    const index = users.value.findIndex((user) => user.id === target.id);
    if (index !== -1) users.value[index] = updated;

    closeEditModal();
    toast.show(`User #${target.id} updated.`);
  } catch (err) {
    toast.show(err instanceof ApiError ? `Update failed: ${err.message}` : "Update failed.");
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <section class="page-heading">
    <div class="th-main">
      <h1>User Management</h1>
      <p>Manage names, emails, and roles.</p>
    </div>

      <div class="th-cell"><small>Sheet</small><b>ADMIN-USR-01</b></div>
    </section>

  <section class="data-panel">
    <div class="panel-header">
      <div>
        <h2>All users</h2>
        <p>Live from the API. Role changes take effect on the user's next load.</p>
      </div>
    </div>

    <div class="table-scroll">
      <table>
        <thead>
          <tr>
            <th>User</th>
            <th>ID</th>
            <th>Role</th>
            <th><span class="sr-only">Actions</span></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in users" :key="user.id">
            <td>
              <div class="user-cell">
                <span class="mini-avatar">{{ initials(user.name) }}</span>
                <span>
                  <router-link
                    :to="{ name: 'admin-user-detail', params: { id: user.id } }"
                    class="order-link user-link"
                  >
                    <strong>{{ user.name }}</strong>
                  </router-link>
                  <small>{{ user.email }}</small>
                </span>
              </div>
            </td>
            <td><code>{{ user.id }}</code></td>
            <td>
              <span :class="['role-badge', user.role]">{{ user.role }}</span>
            </td>
            <td>
              <button
                type="button"
                class="sort-button"
                :aria-label="`Edit user ${user.id}`"
                @click="openEditModal(user)"
              >
                Edit
              </button>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="loading" class="empty-state">Loading users...</p>
      <p v-else-if="loadError" class="empty-state">{{ loadError }}</p>
      <p v-else-if="users.length === 0" class="empty-state">No users yet.</p>
    </div>
  </section>

  <!-- 編輯 Modal：與商品 modal 同語彙（Teleport + Esc/外點/X 關閉 + zod inline 錯誤） -->
  <Teleport to="body">
    <div v-if="editingUser" class="modal-overlay" @click.self="closeEditModal">
      <div
        class="modal"
        role="dialog"
        aria-modal="true"
        :aria-label="`Edit ${editingUser.name}`"
      >
        <div class="modal-header">
          <h3>Edit "{{ editingUser.name }}"</h3>
          <button type="button" class="row-action" aria-label="Close dialog" @click="closeEditModal">
            <Icon name="close" :size="15" />
          </button>
        </div>
        <div class="modal-body product-modal-fields">
          <div class="form-field">
            <label class="account-label" for="u-name">Name</label>
            <input
              id="u-name"
              v-model="userForm.name"
              class="row-edit-field"
              type="text"
              placeholder="Name"
              aria-label="User name"
            />
            <p v-if="userErrors.name" class="field-error">{{ userErrors.name }}</p>
          </div>
          <div class="form-field">
            <label class="account-label" for="u-email">Email</label>
            <input
              id="u-email"
              v-model="userForm.email"
              class="row-edit-field"
              type="email"
              placeholder="user@example.com"
              aria-label="User email"
            />
            <p v-if="userErrors.email" class="field-error">{{ userErrors.email }}</p>
          </div>
          <div class="form-field">
            <label class="account-label" for="u-role">Role</label>
            <select
              id="u-role"
              v-model="userForm.role"
              class="filter-select"
              :disabled="isSelf"
              title="You cannot change your own role"
            >
              <option value="user">user</option>
              <option value="admin">admin</option>
            </select>
            <p v-if="isSelf" class="field-error">
              You cannot change your own role — ask another admin.
            </p>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="ghost-button" @click="closeEditModal">Cancel</button>
          <button type="button" class="primary-button" :disabled="busy" @click="saveEdit">
            Save changes
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
