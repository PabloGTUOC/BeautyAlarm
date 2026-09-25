<script setup lang="ts">
import { computed } from 'vue'
import type { TrackingEntry } from '../types'

const props = defineProps<{ entry: TrackingEntry; busy: boolean }>()
const emit = defineEmits<{ done: [] }>()

const days = computed(() => props.entry.days_since)

/** The count is the thing the screen exists to answer, so it is set separately
 *  from its unit rather than buried in a sentence. Null is stated honestly:
 *  there is no baseline, so there is no number to show. */
/** Zero and null both read as a phrase rather than a figure: "0 done today"
 *  is worse than "Done today", and a missing baseline has no number at all. */
const showNumber = computed(() => days.value !== null && days.value > 0)

const unit = computed(() => {
  if (days.value === null) return 'Not recorded yet'
  if (days.value === 0) return 'Done today'
  return days.value === 1 ? 'day since the last one' : 'days since the last one'
})

const target = computed(() => {
  const t = props.entry.routine.target_interval_days
  return t === null ? null : `Target every ${t} days`
})
</script>

<template>
  <div class="card tracker" :class="{ overdue: entry.overdue }">
    <div class="head">
      <div class="grow">
        <h3 class="title">{{ entry.routine.name }}</h3>
        <p class="count">
          <span v-if="showNumber" class="n">{{ days }}</span>
          <!-- Explicit space: the flex gap is visual only, and without a real
               text node a screen reader announces "23days". -->
          <span class="unit">{{ showNumber ? ` ${unit}` : unit }}</span>
        </p>
      </div>
      <button class="btn" :class="entry.overdue ? 'btn-primary' : ''" :disabled="busy" @click="emit('done')">
        Mark done
      </button>
    </div>

    <p class="meta">
      <!-- The word carries the state, not the tint: colour alone would be
           invisible to a colour-blind user and in bright light. -->
      <span v-if="entry.overdue" class="pill">Overdue</span>
      <span v-if="target">{{ target }}</span>
    </p>
  </div>
</template>

<style scoped>
.tracker {
  padding: 0.875rem 0.875rem 0.75rem;
  transition: background var(--medium) var(--ease), border-color var(--medium) var(--ease);
}
/* A tinted surface, not a coloured edge. */
.tracker.overdue {
  background: var(--danger-surface);
  border-color: var(--danger-border);
}

.head {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
}

.title {
  margin: 0;
  font-size: 1.0625rem;
  font-weight: 600;
  line-height: 1.3;
  letter-spacing: -0.006em;
}

.count {
  display: flex;
  align-items: baseline;
  gap: 0.375rem;
  margin: 0.25rem 0 0;
  color: var(--text-muted);
  font-size: 0.9375rem;
  text-wrap: pretty;
}
.n {
  font-size: 1.5rem;
  font-weight: 680;
  line-height: 1;
  color: var(--text);
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
}
.tracker.overdue .n { color: var(--danger); }

.meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  margin: 0.5rem 0 0;
  font-size: 0.8125rem;
  color: var(--text-muted);
}
.meta:empty { display: none; }

.pill {
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
  background: var(--danger);
  color: var(--surface);
}
</style>
