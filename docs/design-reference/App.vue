<script setup lang="ts">
import { computed, h, ref } from "vue";

type IconName =
  | "activity" | "arrow" | "bolt" | "box" | "chevron" | "close"
  | "database" | "grid" | "logout" | "plus" | "search" | "server"
  | "shield" | "users";

const iconPaths: Record<IconName, string[]> = {
  activity: ["M3 12h4l2.2-6 4.1 12 2.1-6H21"],
  arrow: ["m9 18 6-6-6-6"],
  bolt: ["m13 2-8 12h7l-1 8 8-12h-7l1-8Z"],
  box: ["m4 7 8-4 8 4-8 4-8-4Z", "m4 7 8 4 8-4M4 7v10l8 4 8-4V7M12 11v10"],
  chevron: ["m8 10 4 4 4-4"],
  close: ["m6 6 12 12M18 6 6 18"],
  database: ["M4 5c0-1.7 3.6-3 8-3s8 1.3 8 3-3.6 3-8 3-8-1.3-8-3Z", "M4 5v7c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 12v7c0 1.7 3.6 3 8 3s8-1.3 8-3v-7"],
  grid: ["M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z"],
  logout: ["M10 17l5-5-5-5M15 12H3M15 4h4a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-4"],
  plus: ["M12 5v14M5 12h14"],
  search: ["m21 21-4.4-4.4M19 11a8 8 0 1 1-16 0 8 8 0 0 1 16 0Z"],
  server: ["M5 4h14a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2ZM5 14h14a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-2a2 2 0 0 1 2-2ZM7 7h.01M7 17h.01"],
  shield: ["M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Zm-3-10 2 2 4-4"],
  users: ["M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM22 21v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8"],
};

const Icon = (props: { name: IconName; size?: number }) =>
  h("svg", {
    viewBox: "0 0 24 24",
    width: props.size ?? 18,
    height: props.size ?? 18,
    fill: "none",
    stroke: "currentColor",
    "stroke-width": "1.8",
    "stroke-linecap": "round",
    "stroke-linejoin": "round",
    "aria-hidden": "true",
  }, iconPaths[props.name].map((path) => h("path", { d: path })));

type Order = { id: number; userId: number; customer: string; email: string; time: string };

const initialOrders: Order[] = [
  { id: 1048, userId: 24, customer: "Maya Chen", email: "maya@example.com", time: "2 mins ago" },
  { id: 1047, userId: 18, customer: "Noah Williams", email: "noah@example.com", time: "18 mins ago" },
  { id: 1046, userId: 31, customer: "Amelia Davis", email: "amelia@example.com", time: "42 mins ago" },
  { id: 1045, userId: 12, customer: "Liam Brown", email: "liam@example.com", time: "1 hour ago" },
  { id: 1044, userId: 9, customer: "Sofia Garcia", email: "sofia@example.com", time: "3 hours ago" },
];

const navItems: { label: string; icon: IconName }[] = [
  { label: "Overview", icon: "grid" },
  { label: "Users", icon: "users" },
  { label: "Orders", icon: "box" },
  { label: "API Health", icon: "activity" },
];

const activeNav = ref("Overview");
const orders = ref<Order[]>(initialOrders);
const query = ref("");
const sortDesc = ref(true);
const page = ref(1);
const notice = ref("");

const visibleOrders = computed(() =>
  orders.value
    .filter((order) =>
      `${order.id} ${order.customer} ${order.email} ${order.userId}`.toLowerCase().includes(query.value.toLowerCase()),
    )
    .sort((a, b) => sortDesc.value ? b.id - a.id : a.id - b.id),
);

function initials(name: string) {
  return name.split(" ").map((part) => part[0]).join("");
}

function createOrder() {
  const nextId = Math.max(...orders.value.map((order) => order.id)) + 1;
  orders.value.unshift({
    id: nextId,
    userId: 42,
    customer: "Alex Morgan",
    email: "alex@example.com",
    time: "Just now",
  });
  notice.value = `Order #${nextId} created successfully`;
  window.setTimeout(() => { notice.value = ""; }, 3000);
}
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div>
        <div class="brand">
          <span class="brand-mark"><Icon name="bolt" :size="16" /></span>
          <span>Backend Lab</span>
        </div>
        <nav class="side-nav" aria-label="Main navigation">
          <p class="nav-label">Workspace</p>
          <button
            v-for="item in navItems"
            :key="item.label"
            type="button"
            :class="['nav-item', { active: activeNav === item.label }]"
            @click="activeNav = item.label"
          >
            <Icon :name="item.icon" />
            <span>{{ item.label }}</span>
            <span v-if="item.label === 'API Health'" class="status-dot" />
          </button>
        </nav>
      </div>

      <div class="sidebar-bottom">
        <div class="environment-card">
          <div class="environment-heading"><Icon name="server" :size="16" /><span>Environment</span></div>
          <button type="button" class="environment-select">
            <span><i /> Production</span><Icon name="chevron" :size="14" />
          </button>
        </div>
        <button type="button" class="profile">
          <span class="avatar">AM</span>
          <span class="profile-copy"><strong>Alex Morgan</strong><small>Administrator</small></span>
          <Icon name="logout" :size="17" />
        </button>
      </div>
    </aside>

    <main class="main-content">
      <header class="topbar">
        <div class="mobile-brand">
          <span class="brand-mark"><Icon name="bolt" :size="15" /></span><strong>Backend Lab</strong>
        </div>
        <div class="breadcrumb">
          <span>Backend Lab</span><Icon name="arrow" :size="14" /><strong>{{ activeNav }}</strong>
        </div>
        <div class="topbar-actions">
          <span class="live-pill"><i /> All systems operational</span>
          <button type="button" class="primary-button" @click="createOrder">
            <Icon name="plus" :size="17" />New order
          </button>
        </div>
      </header>

      <div class="mobile-nav">
        <button
          v-for="item in navItems"
          :key="item.label"
          type="button"
          :class="{ active: activeNav === item.label }"
          @click="activeNav = item.label"
        >{{ item.label }}</button>
      </div>

      <div class="content-wrap">
        <section class="page-heading">
          <div>
            <p class="eyebrow">System workspace</p>
            <h1>{{ activeNav }}</h1>
            <p>Monitor your API, users, and order activity from one place.</p>
          </div>
          <p class="updated">Last updated <strong>just now</strong></p>
        </section>

        <section class="metrics" aria-label="Key metrics">
          <article class="metric-card">
            <div class="metric-top"><span class="metric-icon violet"><Icon name="users" /></span><span class="trend">+12.4%</span></div>
            <p>Total users</p><strong>2,849</strong><small>312 joined this month</small>
          </article>
          <article class="metric-card">
            <div class="metric-top"><span class="metric-icon cyan"><Icon name="box" /></span><span class="trend">+8.2%</span></div>
            <p>Total orders</p><strong>8,492</strong><small>642 created this month</small>
          </article>
          <article class="metric-card">
            <div class="metric-top"><span class="metric-icon green"><Icon name="activity" /></span><span class="health-badge"><i /> Healthy</span></div>
            <p>API uptime</p><strong>99.99%</strong><small>Last 30 days</small>
          </article>
          <article class="metric-card">
            <div class="metric-top"><span class="metric-icon amber"><Icon name="database" /></span><span class="latency">24 ms</span></div>
            <p>Database</p><strong>Connected</strong><small>PostgreSQL · production</small>
          </article>
        </section>

        <section class="data-panel">
          <div class="panel-header">
            <div><h2>Recent orders</h2><p>Latest order activity across all users.</p></div>
            <button type="button" class="text-button" @click="activeNav = 'Orders'">
              View all orders <Icon name="arrow" :size="15" />
            </button>
          </div>

          <div class="table-tools">
            <label class="search-field">
              <Icon name="search" :size="17" />
              <input v-model="query" placeholder="Search orders or users..." aria-label="Search orders" />
              <kbd>⌘ K</kbd>
            </label>
            <button type="button" class="sort-button" @click="sortDesc = !sortDesc">
              Order ID: {{ sortDesc ? "Newest" : "Oldest" }}<Icon name="chevron" :size="14" />
            </button>
          </div>

          <div class="table-scroll">
            <table>
              <thead><tr><th>Order ID</th><th>User</th><th>User ID</th><th>Created</th><th><span class="sr-only">Open</span></th></tr></thead>
              <tbody>
                <tr v-for="order in visibleOrders" :key="order.id">
                  <td><span class="order-id">#{{ order.id }}</span></td>
                  <td>
                    <div class="user-cell">
                      <span class="mini-avatar">{{ initials(order.customer) }}</span>
                      <span><strong>{{ order.customer }}</strong><small>{{ order.email }}</small></span>
                    </div>
                  </td>
                  <td><code>usr_{{ String(order.userId).padStart(4, "0") }}</code></td>
                  <td class="muted">{{ order.time }}</td>
                  <td><button type="button" class="row-action" :aria-label="`Open order ${order.id}`"><Icon name="arrow" :size="16" /></button></td>
                </tr>
              </tbody>
            </table>
            <p v-if="visibleOrders.length === 0" class="empty-state">No matching orders found.</p>
          </div>

          <div class="pagination">
            <p>Showing <strong>{{ visibleOrders.length }}</strong> of 8,492 orders</p>
            <div>
              <button type="button" :disabled="page === 1" @click="page = Math.max(1, page - 1)">Previous</button>
              <button v-for="number in [1, 2, 3]" :key="number" type="button" :class="{ current: page === number }" @click="page = number">{{ number }}</button>
              <span>…</span><button type="button" @click="page++">Next</button>
            </div>
          </div>
        </section>

        <section class="security-strip">
          <span class="security-icon"><Icon name="shield" :size="20" /></span>
          <div><strong>Protected by role-based access control</strong><p>JWT authentication, rate limiting, and request size limits are active.</p></div>
          <span class="security-status"><i /> Security checks passed</span>
        </section>
      </div>
    </main>

    <Transition name="toast">
      <div v-if="notice" class="toast" role="status">
        <span><Icon name="shield" :size="17" /></span>{{ notice }}
        <button type="button" aria-label="Dismiss notification" @click="notice = ''"><Icon name="close" :size="15" /></button>
      </div>
    </Transition>
  </div>
</template>
