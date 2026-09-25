<script setup lang="ts">
import { computed } from 'vue'
import { trimSeconds } from '../dates'
import { describeProducts } from '../products'
import type { LogStatus, TodayEntry } from '../types'

const props = defineProps<{ entry: TodayEntry; busy: boolean }>()
const emit = defineEmits<{ log: [LogStatus]; undo: [] }>()

const status = computed(() => props.entry.log?.status ?? null)
const products = computed(() => props.entry.routine.products ?? [])

/** What to apply, in order (D8a). One tick covers the whole routine (D6), so
 *  these are steps to follow, not checkboxes. */
const steps = computed(() => describeProducts(products.value))

const time = computed(() => trimSeconds(props.entry.routine.notification_time))
</script>

<template>
  <div class="card row-card" :class="{ done: status === 'completed', skipped: status === 'skipped' }">
    <div class="head">
      <h3 class="title" :class="{ strike: status === 'completed' }">{{ entry.routine.name }}</h3>

      <div v-if="status" class="actions">
        <button class="btn" :disabled="busy" @click="emit('undo')">Undo</button>
      </div>
      <div v-else class="actions">
        <button class="btn" :disabled="busy" @click="emit('log', 'skipped')">Skip</button>
        <button class="btn btn-primary" :disabled="busy" @click="emit('log', 'completed')">
          Done
        </button>
      </div>
    </div>

    <!-- Full width, below the actions rather than beside them: a three-product
         stack wrapped to three lines when it was boxed into half the row. -->
    <p v-if="products.length" class="steps">{{ steps }}</p>

    <p class="meta">
      <span v-if="status === 'completed'" class="state">Done</span>
      <span v-else-if="status === 'skipped'" class="state">Skipped</span>
      <span v-if="time">{{ time }}</span>
    </p>
  </div>
</template>

<style scoped>
.row-card {
  padding: 0.875rem 0.875rem 0.75rem;
  transition: opacity var(--medium) var(--ease), background var(--medium) var(--ease);
}
.row-card.done,
.row-card.skipped { background: var(--surface-alt); }
.row-card.done { opacity: 0.72; }

.head {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.title {
  flex: 1;
  min-width: 0;
  margin: 0;
  font-size: 1.0625rem;
  font-weight: 600;
  line-height: 1.3;
  letter-spacing: -0.006em;
}

.steps {
  margin: 0.5rem 0 0;
  font-size: 0.875rem;
  line-height: 1.5;
  color: var(--text-muted);
  text-wrap: pretty;
}

.meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem 0.625rem;
  margin: 0.375rem 0 0;
  font-size: 0.8125rem;
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}
.meta:empty { display: none; }
.state { font-weight: 650; }
</style>
