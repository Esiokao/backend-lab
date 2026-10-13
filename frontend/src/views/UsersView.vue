<script setup lang="ts">
import { onMounted, ref } from "vue";

import { ApiError, api } from "@/lib/api";

// 使用者型別（後端只回傳公開欄位）。
type User = { id: number; name: string; email: string };

const users = ref<User[]>([]);
const loading = ref(true);
const loadError = ref("");

onMounted(async () => {
  try {
    users.value = await api.get<User[]>("/users");
  } catch (err) {
    loadError.value =
      err instanceof ApiError ? `Failed to load users: ${err.message}` : "Failed to load users.";
  } finally {
    loading.value = false;
  }
});

// 名字取前兩字做頭像縮寫。
function initials(name: string): string {
  return name.trim().slice(0, 2).toUpperCase();
}
</script>

<template>
  <section class="page-heading">
    <div>
      <p class="eyebrow">System workspace</p>
      <h1>Users</h1>
      <p>Everyone with access to the workspace.</p>
    </div>
  </section>

  <section class="data-panel">
    <div class="panel-header">
      <div>
        <h2>All users</h2>
        <p>Live from the API.</p>
      </div>
    </div>

    <div class="table-scroll">
      <table>
        <thead>
          <tr>
            <th>User</th>
            <th>ID</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in users" :key="user.id">
            <td>
              <div class="user-cell">
                <span class="mini-avatar">{{ initials(user.name) }}</span>
                <span>
                  <strong>{{ user.name }}</strong>
                  <small>{{ user.email }}</small>
                </span>
              </div>
            </td>
            <td>
              <code>{{ user.id }}</code>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="loading" class="empty-state">Loading users...</p>
      <p v-else-if="loadError" class="empty-state">{{ loadError }}</p>
      <p v-else-if="users.length === 0" class="empty-state">No users yet.</p>
    </div>
  </section>
</template>
