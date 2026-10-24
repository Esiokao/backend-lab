<script setup lang="ts">
import { onMounted, ref } from "vue";

import Icon from "@/components/Icon.vue";
import { ApiError, api } from "@/lib/api";
import { useToast } from "@/stores/toast";

// 通知管理（F11 admin UI）：
// - 定向通知：POST /admin/notifications（202，經 Outbox → worker 異步投遞）
// - 廣播公告：POST /admin/notifications/broadcasts（同步寫入公告表）
// - 廣播歷史：GET /notifications/broadcasts、DELETE /admin/notifications/broadcasts/{id}

type UserRow = { id: number; name: string; email: string; role: string };

type Broadcast = {
  id: number;
  type: string;
  title: string;
  body: string;
  created_at: string;
};

const toast = useToast();

const users = ref<UserRow[]>([]);
const broadcasts = ref<Broadcast[]>([]);
const broadcastsLoading = ref(true);
const busy = ref(false);

const targetForm = ref({ userId: "", title: "", body: "" });
const broadcastForm = ref({ title: "", body: "" });

async function loadUsers(): Promise<void> {
  try {
    users.value = await api.get<UserRow[]>("/users");
  } catch (err) {
    toast.show(
      err instanceof ApiError ? `Failed to load users: ${err.message}` : "Failed to load users.",
    );
  }
}

async function loadBroadcasts(): Promise<void> {
  broadcastsLoading.value = true;
  try {
    const data = await api.get<{ items: Broadcast[] }>("/notifications/broadcasts");
    broadcasts.value = data.items;
  } catch (err) {
    toast.show(
      err instanceof ApiError
        ? `Failed to load broadcasts: ${err.message}`
        : "Failed to load broadcasts.",
    );
  } finally {
    broadcastsLoading.value = false;
  }
}

async function sendTargeted(): Promise<void> {
  const { userId, title, body } = targetForm.value;

  if (!userId) {
    toast.show("Select a recipient first.");
    return;
  }
  if (!title.trim() || !body.trim()) {
    toast.show("Title and message are required.");
    return;
  }

  busy.value = true;
  try {
    await api.post("/admin/notifications", {
      user_id: Number(userId),
      title: title.trim(),
      body: body.trim(),
    });
    // 202：事件進 Outbox，由背景 worker 投遞，非即時。
    toast.show(`Notification queued for "${users.value.find((u) => u.id === Number(userId))?.name ?? "user"}".`);
    targetForm.value = { userId: "", title: "", body: "" };
  } catch (err) {
    toast.show(
      err instanceof ApiError ? `Send failed: ${err.message}` : "Send failed.",
    );
  } finally {
    busy.value = false;
  }
}

async function sendBroadcast(): Promise<void> {
  const { title, body } = broadcastForm.value;

  if (!title.trim() || !body.trim()) {
    toast.show("Title and message are required.");
    return;
  }

  busy.value = true;
  try {
    await api.post("/admin/notifications/broadcasts", {
      title: title.trim(),
      body: body.trim(),
    });
    toast.show("Broadcast published.");
    broadcastForm.value = { title: "", body: "" };
    await loadBroadcasts();
  } catch (err) {
    toast.show(
      err instanceof ApiError ? `Broadcast failed: ${err.message}` : "Broadcast failed.",
    );
  } finally {
    busy.value = false;
  }
}

async function deleteBroadcast(broadcast: Broadcast): Promise<void> {
  if (!window.confirm(`Delete broadcast "${broadcast.title}"?`)) return;

  busy.value = true;
  try {
    await api.delete(`/admin/notifications/broadcasts/${broadcast.id}`);
    toast.show(`Broadcast "${broadcast.title}" deleted.`);
    await loadBroadcasts();
  } catch (err) {
    toast.show(
      err instanceof ApiError ? `Delete failed: ${err.message}` : "Delete failed.",
    );
  } finally {
    busy.value = false;
  }
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString();
}

onMounted(() => {
  void loadUsers();
  void loadBroadcasts();
});
</script>

<template>
  <section class="page-heading">
    <div class="th-main">
      <h1>Notifications</h1>
      <p>Send targeted notifications or publish announcements.</p>
    </div>

      <div class="th-cell"><small>Sheet</small><b>ADMIN-NTF-01</b></div>
    </section>

  <div class="admin-notifications-grid">
    <section class="data-panel" aria-label="Send general notification">
      <div class="panel-header">
        <div>
          <h2>General notification</h2>
          <p>Targeted at one user — delivered to their general feed via the background worker.</p>
        </div>
      </div>
      <div class="notify-form">
        <select v-model="targetForm.userId" class="filter-select" aria-label="Recipient">
          <option value="" disabled>Select recipient…</option>
          <option v-for="user in users" :key="user.id" :value="String(user.id)">
            {{ user.name }} — {{ user.email }}
          </option>
        </select>
        <input
          v-model="targetForm.title"
          class="row-edit-field"
          type="text"
          placeholder="Title"
          aria-label="Notification title"
        />
        <textarea
          v-model="targetForm.body"
          class="row-edit-field notify-body"
          placeholder="Message"
          aria-label="Notification message"
        />
        <div class="order-actions">
          <button type="button" class="primary-button" :disabled="busy" @click="sendTargeted">
            <Icon name="bell" :size="14" /> Send
          </button>
        </div>
      </div>
    </section>

    <section class="data-panel" aria-label="Publish system broadcast">
      <div class="panel-header">
        <div>
          <h2>System broadcast</h2>
          <p>Published instantly to every user's system feed.</p>
        </div>
      </div>
      <div class="notify-form">
        <input
          v-model="broadcastForm.title"
          class="row-edit-field"
          type="text"
          placeholder="Title"
          aria-label="Broadcast title"
        />
        <textarea
          v-model="broadcastForm.body"
          class="row-edit-field notify-body"
          placeholder="Message"
          aria-label="Broadcast message"
        />
        <div class="order-actions">
          <button type="button" class="primary-button" :disabled="busy" @click="sendBroadcast">
            <Icon name="plus" :size="14" /> Publish
          </button>
        </div>
      </div>
    </section>
  </div>

    <section class="data-panel">
      <div class="panel-header">
        <div>
          <h2>System broadcast history</h2>
          <p>{{ broadcasts.length }} broadcast{{ broadcasts.length === 1 ? "" : "s" }} published.</p>
        </div>
      </div>
    <div class="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Title</th>
            <th>Message</th>
            <th>Published</th>
            <th><span class="sr-only">Actions</span></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="broadcast in broadcasts" :key="broadcast.id">
            <td><strong>{{ broadcast.title }}</strong></td>
            <td><span class="broadcast-body">{{ broadcast.body }}</span></td>
            <td><span class="order-date">{{ formatTime(broadcast.created_at) }}</span></td>
            <td>
              <button
                type="button"
                class="row-action row-delete"
                :aria-label="`Delete broadcast ${broadcast.title}`"
                :disabled="busy"
                @click="deleteBroadcast(broadcast)"
              >
                <Icon name="close" :size="14" />
              </button>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="broadcastsLoading" class="empty-state">Loading broadcasts...</p>
      <p v-else-if="broadcasts.length === 0" class="empty-state">No system broadcasts yet.</p>
    </div>
  </section>
</template>
