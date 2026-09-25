<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useRoutinesStore } from '../stores/routines'
import { describeDays, trimSeconds } from '../dates'
import { describeProducts } from '../products'
import type { Routine } from '../types'

const store = useRoutinesStore()
const actionError = ref<string | null>(null)

function summary(routine: Routine): string {
  // A tracked routine has no weekdays and no slot: its cadence is the interval.
  const parts =
    routine.kind === 'tracked'
      ? [`every ${routine.target_interval_days} days`]
      : [describeDays(routine.days_of_week ?? []), routine.time_period ?? '']
  const time = trimSeconds(routine.notification_time)
  if (time) parts.push(time)
  if (!routine.is_active) parts.push('paused')
  return parts.filter(Boolean).join(' · ')
}

/** The products in application order, or nothing for an action or service. */
function steps(routine: Routine): string {
  return describeProducts(routine.products)
}

async function remove(routine: Routine): Promise<void> {
  if (!confirm(`Delete ${routine.name} and its history?`)) return
  actionError.value = null
  try {
    await store.remove(routine.id)
  } catch (err) {
    actionError.value = err instanceof Error ? err.message : String(err)
  }
}

onMounted(() => store.load())
</script>

<template>
  <header class="app-header">
    <h1>Routines</h1>
    <RouterLink class="btn btn-primary" to="/routines/new">Add</RouterLink>
  </header>

  <p v-if="store.error" class="banner banner-error">{{ store.error }}</p>
  <p v-if="actionError" class="banner banner-error">{{ actionError }}</p>
  <p v-if="store.loading" class="muted">Loading…</p>

  <p v-else-if="store.routines.length === 0" class="empty">
    No routines yet. Add the first one.
  </p>

  <div v-for="routine in store.routines" :key="routine.id" class="card routine">
    <div class="head">
      <h3 class="title">{{ routine.name }}</h3>
      <span v-if="routine.kind === 'tracked'" class="tag">Tracked</span>
    </div>
    <p v-if="routine.products.length" class="steps">{{ steps(routine) }}</p>
    <p class="summary">{{ summary(routine) }}</p>
    <div class="actions">
      <RouterLink class="btn" :to="`/routines/${routine.id}`">Edit</RouterLink>
      <button class="btn btn-danger" @click="remove(routine)">Delete</button>
    </div>
  </div>
</template>

<style scoped>
.routine { padding: 0.875rem; }

.head {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.title {
  margin: 0;
  font-size: 1.0625rem;
  font-weight: 600;
  line-height: 1.3;
  letter-spacing: -0.006em;
}

.tag {
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  padding: 0.1rem 0.4rem;
  border-radius: 999px;
  border: 1px solid var(--accent-border);
  background: var(--accent-surface);
  color: var(--accent);
}

.steps {
  margin: 0.375rem 0 0;
  font-size: 0.875rem;
  line-height: 1.5;
  color: var(--text-muted);
  text-wrap: pretty;
}

.summary {
  margin: 0.25rem 0 0;
  font-size: 0.8125rem;
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}

/* Full-width actions on their own line: side by side with the text they left
   the name about half a screen wide. */
.routine .actions { margin-top: 0.75rem; }
.routine .actions > * { flex: 1; }
</style>
