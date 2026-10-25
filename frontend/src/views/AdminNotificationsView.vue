<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";

import Icon from "@/components/Icon.vue";
import { ApiError, api } from "@/lib/api";
import { useToast } from "@/stores/toast";

// 通知管理（F11 admin UI）：
// - 定向通知：POST /admin/notifications（202，經 Outbox → worker 異步投遞）
// - 廣播公告：POST /admin/notifications/broadcasts（同步寫入公告表）
// - 廣播歷史：GET /notifications/broadcasts、DELETE /admin/notifications/broadcasts/{id}
// v1.19：通知範本（localStorage 持久化，前端側）—— 常用公告（如系統維護更新）
// 存成範本，下次套用免重新輸入。後端尚無 templates 端點，故存 client-side（記帳：待後端補）。

type UserRow = { id: number; name: string; email: string; role: string };

type Broadcast = {
  id: number;
  type: string;
  title: string;
  body: string;
  created_at: string;
};

type NotifTemplate = {
  id: number;
  name: string;
  scope: "general" | "broadcast";
  title: string;
  body: string;
  created_at: string;
};

const TEMPLATES_KEY = "bl-notif-templates";

const toast = useToast();

const users = ref<UserRow[]>([]);
const broadcasts = ref<Broadcast[]>([]);
const broadcastsLoading = ref(true);
const busy = ref(false);

const targetForm = ref({ userId: "", title: "", body: "" });
const broadcastForm = ref({ title: "", body: "" });

// ── 通知範本（localStorage；首訪種一個「系統維護更新」範例，可刪） ──

const templates = ref<NotifTemplate[]>([]);
const templateModalOpen = ref(false);
const templateName = ref("");
const templateScope = ref<"general" | "broadcast">("broadcast");
const templateDraft = ref({ title: "", body: "" });

function loadTemplates(): void {
  try {
    const raw = localStorage.getItem(TEMPLATES_KEY);
    if (raw !== null) {
      templates.value = JSON.parse(raw) as NotifTemplate[];
      return;
    }
  } catch {
    // 壞掉的快取當空列表，下次儲存會覆寫。
  }
  templates.value = [
    {
      id: 1,
      name: "系統維護更新",
      scope: "broadcast",
      title: "系統維護公告",
      body: "系統將於今晚 23:00–24:00 進行維護更新，期間服務可能短暫中斷，敬請見諒。",
      created_at: new Date().toISOString(),
    },
  ];
  persistTemplates();
}

function persistTemplates(): void {
  localStorage.setItem(TEMPLATES_KEY, JSON.stringify(templates.value));
}

function applyTemplate(template: NotifTemplate): void {
  if (template.scope === "general") {
    targetForm.value.title = template.title;
    targetForm.value.body = template.body;
  } else {
    broadcastForm.value.title = template.title;
    broadcastForm.value.body = template.body;
  }
  toast.show(`Template "${template.name}" applied.`);
}

// 從表單存範本：兩個表單誰有內容就存誰（都沒內容 → 提示）。
function openTemplateModal(): void {
  const hasTarget = targetForm.value.title.trim() !== "" || targetForm.value.body.trim() !== "";
  const hasBroadcast =
    broadcastForm.value.title.trim() !== "" || broadcastForm.value.body.trim() !== "";
  if (!hasTarget && !hasBroadcast) {
    toast.show("Fill in a title and message first, then save it as a template.");
    return;
  }
  if (hasTarget) {
    templateScope.value = "general";
    templateDraft.value = { title: targetForm.value.title, body: targetForm.value.body };
  } else {
    templateScope.value = "broadcast";
    templateDraft.value = { title: broadcastForm.value.title, body: broadcastForm.value.body };
  }
  templateName.value = templateDraft.value.title.trim();
  templateModalOpen.value = true;
}

function closeTemplateModal(): void {
  templateModalOpen.value = false;
}

function saveTemplate(): void {
  const name = templateName.value.trim();
  if (!name) {
    toast.show("Template name is required.");
    return;
  }
  templates.value = [
    ...templates.value,
    {
      id: Date.now(),
      name,
      scope: templateScope.value,
      title: templateDraft.value.title.trim(),
      body: templateDraft.value.body.trim(),
      created_at: new Date().toISOString(),
    },
  ];
  persistTemplates();
  closeTemplateModal();
  toast.show(`Template "${name}" saved.`);
}

function deleteTemplate(template: NotifTemplate): void {
  if (!window.confirm(`Delete template "${template.name}"?`)) return;
  templates.value = templates.value.filter((t) => t.id !== template.id);
  persistTemplates();
  toast.show(`Template "${template.name}" deleted.`);
}

function onTemplateKeydown(event: KeyboardEvent): void {
  if (event.key === "Escape" && templateModalOpen.value) closeTemplateModal();
}

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
  loadTemplates();
  void loadUsers();
  void loadBroadcasts();
  document.addEventListener("keydown", onTemplateKeydown);
});

onUnmounted(() => {
  document.removeEventListener("keydown", onTemplateKeydown);
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
          <button type="button" class="text-button" :disabled="busy" @click="openTemplateModal">
            Save as template
          </button>
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
          <button type="button" class="text-button" :disabled="busy" @click="openTemplateModal">
            Save as template
          </button>
          <button type="button" class="primary-button" :disabled="busy" @click="sendBroadcast">
            <Icon name="plus" :size="14" /> Publish
          </button>
        </div>
      </div>
    </section>
  </div>

  <!-- 通知範本：套用填回表單（scope 決定填哪個）；存/刪走 localStorage（前端側） -->
  <section class="data-panel template-panel" aria-label="Notification templates">
    <div class="panel-header">
      <div>
        <h2>Templates</h2>
        <p>Saved announcements for reuse — apply fills the form above.</p>
      </div>
    </div>
    <div class="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Name</th>
            <th>Scope</th>
            <th>Title</th>
            <th>Message</th>
            <th><span class="sr-only">Actions</span></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="template in templates" :key="template.id">
            <td><strong>{{ template.name }}</strong></td>
            <td><span class="zone">{{ template.scope === "general" ? "General" : "Broadcast" }}</span></td>
            <td>{{ template.title }}</td>
            <td><span class="broadcast-body">{{ template.body }}</span></td>
            <td>
              <div class="order-actions">
                <button
                  type="button"
                  class="sort-button"
                  :aria-label="`Apply template ${template.name}`"
                  @click="applyTemplate(template)"
                >
                  Use
                </button>
                <button
                  type="button"
                  class="row-action row-delete"
                  :aria-label="`Delete template ${template.name}`"
                  @click="deleteTemplate(template)"
                >
                  <Icon name="close" :size="14" />
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="templates.length === 0" class="empty-state">
        No templates yet — fill a form and press "Save as template".
      </p>
    </div>
  </section>

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

  <!-- 範本命名 Modal：把當前表單內容存成範本 -->
  <Teleport to="body">
    <div v-if="templateModalOpen" class="modal-overlay" @click.self="closeTemplateModal">
      <div class="modal" role="dialog" aria-modal="true" aria-label="Save template">
        <div class="modal-header">
          <h3>Save as template</h3>
          <button type="button" class="row-action" aria-label="Close dialog" @click="closeTemplateModal">
            <Icon name="close" :size="15" />
          </button>
        </div>
        <div class="modal-body product-modal-fields">
          <div class="form-field">
            <label class="account-label" for="t-name">Template name</label>
            <input
              id="t-name"
              v-model="templateName"
              class="row-edit-field"
              type="text"
              placeholder="e.g. 系統維護更新"
              aria-label="Template name"
              @keydown.enter="saveTemplate"
            />
          </div>
          <div class="form-field">
            <label class="account-label" for="t-scope">Applies to</label>
            <select id="t-scope" v-model="templateScope" class="filter-select" disabled>
              <option value="general">General notification</option>
              <option value="broadcast">System broadcast</option>
            </select>
          </div>
          <p class="order-create-hint">
            Preview: {{ templateDraft.title }} — {{ templateDraft.body.slice(0, 60) }}{{ templateDraft.body.length > 60 ? "…" : "" }}
          </p>
        </div>
        <div class="modal-footer">
          <button type="button" class="ghost-button" @click="closeTemplateModal">Cancel</button>
          <button type="button" class="primary-button" @click="saveTemplate">Save template</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
