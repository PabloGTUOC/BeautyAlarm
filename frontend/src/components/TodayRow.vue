<script setup lang="ts">
import { computed } from 'vue'
import { trimSeconds } from '../dates'
import type { LogStatus, TodayEntry } from '../types'

const props = defineProps<{ entry: TodayEntry; busy: boolean }>()
const emit = defineEmits<{ log: [LogStatus]; undo: [] }>()

const status = computed(() => props.entry.log?.status ?? null)
const product = computed(() => props.entry.routine.product)
const subtitle = computed(() => {
  const parts: string[] = []
  if (product.value?.brand) parts.push(product.value.brand)
  const time = trimSeconds(props.entry.routine.notification_time)
  if (time) parts.push(time)
  return parts.join(' · ')
})
</script>

<template>
  <div class="card">
    <div class="row">
      <div class="grow">
        <div :class="{ strike: status === 'completed' }">
          {{ product?.name ?? 'Unknown product' }}
        </div>
        <div v-if="subtitle" class="muted">{{ subtitle }}</div>
      </div>

      <div v-if="status" class="actions">
        <span class="muted">{{ status === 'completed' ? 'Done' : 'Skipped' }}</span>
        <button class="btn" :disabled="busy" @click="emit('undo')">Undo</button>
      </div>
      <div v-else class="actions">
        <button class="btn" :disabled="busy" @click="emit('log', 'skipped')">Skip</button>
        <button class="btn btn-primary" :disabled="busy" @click="emit('log', 'completed')">
          Done
        </button>
      </div>
    </div>
  </div>
</template>
