<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useRoutinesStore } from '../stores/routines'
import { describeDays, trimSeconds } from '../dates'
import type { Routine } from '../types'

const store = useRoutinesStore()
const actionError = ref<string | null>(null)

function summary(routine: Routine): string {
  const parts = [describeDays(routine.days_of_week), routine.time_period]
  const time = trimSeconds(routine.notification_time)
  if (time) parts.push(time)
  if (!routine.is_active) parts.push('paused')
  return parts.join(' · ')
}

async function remove(routine: Routine): Promise<void> {
  const name = routine.product?.name ?? 'this routine'
  if (!confirm(`Delete ${name} and its history?`)) return
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

  <div v-for="routine in store.routines" :key="routine.id" class="card">
    <div class="row">
      <div class="grow">
        <div>{{ routine.product?.name ?? 'Unknown product' }}</div>
        <div class="muted">{{ summary(routine) }}</div>
      </div>
      <div class="actions">
        <RouterLink class="btn" :to="`/routines/${routine.id}`">Edit</RouterLink>
        <button class="btn btn-danger" @click="remove(routine)">Delete</button>
      </div>
    </div>
  </div>
</template>
