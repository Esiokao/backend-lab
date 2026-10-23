<script setup lang="ts">
import { onMounted, ref } from "vue";

import Icon from "@/components/Icon.vue";
import { ApiError, api } from "@/lib/api";
import { useAuth } from "@/stores/auth";
import { useToast } from "@/stores/toast";

// Admin 使用者管理（F9）。後端契約（以 repo 為準）：
// - GET /users（admin-only）→ UserResponse[]（含 role）
// - PATCH /admin/users/{id}（name/email/role；改自己的 role → 400；email 衝突 → 409）
// - 後端尚無 DELETE /admin/users/{id} 與 GET /admin/users/{id} → 刪除與詳情功能待後端補（記帳中）

type UserRow = { id: number; name: string; email: string; role: "user" | "admin" };

const { user: currentUser } = useAuth();
const toast = useToast();

const users = ref<UserRow[]>([]);
const loading = ref(true);
const loadError = ref("");
const editingId = ref<number | null>(null);
const editForm = ref<{ name: string; email: string; role: "user" | "admin" }>({
  name: "",
  email: "",
  role: "user",
});

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

onMounted(loadUsers);

// 名字取前兩字做頭像縮寫。
function initials(name: string): string {
  return name.trim().slice(0, 2).toUpperCase();
}

function startEdit(user: UserRow): void {
  editingId.value = user.id;
  editForm.value = { name: user.name, email: user.email, role: user.role };
}

function cancelEdit(): void {
  editingId.value = null;
}

async function saveEdit(target: UserRow): Promise<void> {
  try {
    const updated = await api.patch<UserRow>(`/admin/users/${target.id}`, {
      name: editForm.value.name,
      email: editForm.value.email,
      role: editForm.value.role,
    });

    const index = users.value.findIndex((user) => user.id === target.id);
    if (index !== -1) users.value[index] = updated;

    editingId.value = null;
    toast.show(`User #${target.id} updated.`);
  } catch (err) {
    toast.show(err instanceof ApiError ? `Update failed: ${err.message}` : "Update failed.");
  }
}
</script>

<template>
  <section class="page-heading">
    <div>
      <p class="eyebrow">Administration</p>
      <h1>User Management</h1>
      <p>Manage names, emails, and roles.</p>
    </div>
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
            <template v-if="editingId === user.id">
              <td>
                <div class="user-cell">
                  <span class="mini-avatar">{{ initials(editForm.name) }}</span>
                  <span>
                    <input
                      v-model="editForm.name"
                      class="row-edit-field"
                      type="text"
                      :aria-label="`Name for user ${user.id}`"
                    />
                    <input
                      v-model="editForm.email"
                      class="row-edit-field"
                      style="margin-top: 4px"
                      type="email"
                      :aria-label="`Email for user ${user.id}`"
                    />
                  </span>
                </div>
              </td>
              <td><code>{{ user.id }}</code></td>
              <td>
                <!-- 防呆同後端：不能改自己的 role（會被鎖在門外）。 -->
                <select
                  v-model="editForm.role"
                  class="filter-select"
                  :aria-label="`Role for user ${user.id}`"
                  :disabled="currentUser?.id === user.id"
                  title="You cannot change your own role"
                >
                  <option value="user">user</option>
                  <option value="admin">admin</option>
                </select>
              </td>
              <td>
                <div class="order-actions">
                  <button type="button" class="sort-button" @click="saveEdit(user)">Save</button>
                  <button
                    type="button"
                    class="row-action"
                    aria-label="Cancel editing"
                    @click="cancelEdit"
                  >
                    <Icon name="close" :size="15" />
                  </button>
                </div>
              </td>
            </template>
            <template v-else>
              <td>
                <div class="user-cell">
                  <span class="mini-avatar">{{ initials(user.name) }}</span>
                  <span>
                    <strong>{{ user.name }}</strong>
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
                  @click="startEdit(user)"
                >
                  Edit
                </button>
              </td>
            </template>
          </tr>
        </tbody>
      </table>
      <p v-if="loading" class="empty-state">Loading users...</p>
      <p v-else-if="loadError" class="empty-state">{{ loadError }}</p>
      <p v-else-if="users.length === 0" class="empty-state">No users yet.</p>
    </div>
  </section>
</template>
