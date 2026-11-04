<script setup lang="ts">
// 可搜尋的下拉選單（@headlessui/vue Combobox 包裝）。
// 帳號一多時原生 <select> 無法定位——這裡把「輸入框本身當搜尋」，
// 鍵盤導航 / 點外關閉 / aria 交給 headless UI，本元件只管選項過濾與樣式。
// 樣式走 Tailwind + tailwind.css 的 @theme tokens（跟 design.css 主題變數連動）。
import { computed, ref } from "vue";

import {
  Combobox,
  ComboboxInput,
  ComboboxOption,
  ComboboxOptions,
} from "@headlessui/vue";

const props = defineProps<{
  modelValue: string;
  options: { value: string; label: string }[];
  placeholder?: string;
  ariaLabel?: string;
}>();

const emit = defineEmits<{ "update:modelValue": [value: string] }>();

const query = ref("");

const filtered = computed(() => {
  const q = query.value.trim().toLowerCase();
  if (!q) return props.options;
  return props.options.filter((o) => o.label.toLowerCase().includes(q));
});

const selectedLabel = computed(
  () => props.options.find((o) => o.value === props.modelValue)?.label ?? "",
);

function onSelect(value: string): void {
  emit("update:modelValue", value);
}
</script>

<template>
  <Combobox :model-value="modelValue" @update:model-value="onSelect">
    <div class="relative w-full">
      <ComboboxInput
        class="select-chevron h-[34px] w-full rounded-[7px] border border-line bg-card py-0 pr-7 pl-2.5 text-xs text-ink focus:border-brand focus:outline-0"
        :display-value="() => selectedLabel"
        :placeholder="placeholder"
        :aria-label="ariaLabel"
        autocomplete="off"
        @change="query = $event.target.value"
      />
      <ComboboxOptions
        class="absolute inset-x-0 top-[calc(100%+4px)] z-30 max-h-60 overflow-y-auto m-0 list-none rounded-[7px] border border-line bg-card p-1 shadow-lg"
      >
        <li v-if="filtered.length === 0" class="px-2.5 py-2.5 text-xs text-ink-faint">
          No match
        </li>
        <ComboboxOption
          v-for="option in filtered"
          :key="option.value"
          :value="option.value"
          v-slot="{ active, selected }"
        >
          <li
            :class="[
              'flex items-center justify-between gap-2 rounded-[5px] px-2.5 py-1.5 text-xs text-ink cursor-pointer',
              active ? 'bg-brand/15' : '',
              selected ? 'font-semibold' : '',
            ]"
          >
            <span>{{ option.label }}</span>
            <span v-if="selected" class="text-brand">✓</span>
          </li>
        </ComboboxOption>
      </ComboboxOptions>
    </div>
  </Combobox>
</template>
