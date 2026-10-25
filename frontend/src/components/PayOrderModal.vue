<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";

import Icon from "@/components/Icon.vue";
import { ApiError, api } from "@/lib/api";
import { useToast } from "@/stores/toast";

// 付款 Modal（v1.20）：與 checkout 付款頁同一語彙——明細、Backend Lab Pay、demo 聲明。
// 按下 Pay 才真的 POST /orders/{id}/pay（後端僅允許 created → pending、限本人）；
// 成功後由父層重載訂單。

export type PayLine = { name: string; quantity: number; amount: number };

const props = defineProps<{
  orderId: number;
  lines: PayLine[];
}>();

const emit = defineEmits<{ close: []; paid: [] }>();

const toast = useToast();
const paying = ref(false);
const failed = ref("");

const total = computed(() => `$${props.lines.reduce((sum, l) => sum + l.amount, 0).toFixed(2)}`);

function lineTotal(line: PayLine): string {
  return `$${line.amount.toFixed(2)}`;
}

async function pay(): Promise<void> {
  paying.value = true;
  failed.value = "";
  try {
    await api.post(`/orders/${props.orderId}/pay`);
    toast.show(`Order #${props.orderId} paid.`);
    emit("paid");
  } catch (err) {
    failed.value = err instanceof ApiError ? err.message : "Payment failed.";
  } finally {
    paying.value = false;
  }
}

function onKeydown(event: KeyboardEvent): void {
  if (event.key === "Escape") emit("close");
}

onMounted(() => document.addEventListener("keydown", onKeydown));
onUnmounted(() => document.removeEventListener("keydown", onKeydown));
</script>

<template>
  <Teleport to="body">
    <div class="modal-overlay" @click.self="emit('close')">
      <div class="modal pay-modal" role="dialog" aria-modal="true" :aria-label="`Pay order #${orderId}`">
        <div class="modal-header">
          <h3>Pay order #{{ orderId }}</h3>
          <button type="button" class="row-action" aria-label="Close dialog" @click="emit('close')">
            <Icon name="close" :size="15" />
          </button>
        </div>
        <div class="modal-body pay-modal-body">
          <p v-if="failed" class="login-error">{{ failed }}</p>

          <div class="pay-method">
            <label class="payment-option">
              <input type="radio" name="payment" checked disabled />
              <span class="payment-option-icon"><Icon name="shield" :size="16" /></span>
              <span>
                <strong>Backend Lab Pay</strong>
                <small>Demo payment — simulated instantly, no real charge.</small>
              </span>
            </label>
          </div>

          <ul class="pay-lines">
            <li v-for="line in lines" :key="line.name">
              <span class="pay-line-name">{{ line.name }} × {{ line.quantity }}</span>
              <span class="order-total">{{ lineTotal(line) }}</span>
            </li>
          </ul>

          <div class="pay-total-row">
            <small>Total due now</small>
            <span class="cart-total">{{ total }}</span>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="ghost-button" :disabled="paying" @click="emit('close')">
            Cancel
          </button>
          <button type="button" class="primary-button pay-button" :disabled="paying" @click="pay">
            <Icon name="bolt" :size="15" />
            {{ paying ? "Paying..." : `Pay ${total}` }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
