<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import TodayRow from '../components/TodayRow.vue'
import { api } from '../api'
import { fromLocalIsoDate } from '../dates'
import type { LogStatus, TodayEntry, TodayResponse } from '../types'

const data = ref<TodayResponse | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const busyRoutine = ref<number | null>(null)

const morning = computed(() => entriesFor('morning'))
const night = computed(() => entriesFor('night'))

const heading = computed(() => {
  if (!data.value) return ''
  return fromLocalIsoDate(data.value.date).toLocaleDateString(undefined, {
    weekday: 'long',
    day: 'numeric',
    month: 'long'
  })
})

function entriesFor(period: 'morning' | 'night'): TodayEntry[] {
  return (data.value?.entries ?? []).filter((e) => e.routine.time_period === period)
}

async function load(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    data.value = await api.today()
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
}

async function log(entry: TodayEntry, status: LogStatus): Promise<void> {
  busyRoutine.value = entry.routine.id
  try {
    await api.logRoutine(entry.routine.id, status, data.value?.date)
    await load()
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    busyRoutine.value = null
  }
}

async function undo(entry: TodayEntry): Promise<void> {
  if (!entry.log) return
  busyRoutine.value = entry.routine.id
  try {
    await api.deleteLog(entry.log.id)
    await load()
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    busyRoutine.value = null
  }
}

onMounted(load)
</script>

<template>
  <header class="app-header">
    <h1>Today</h1>
    <span class="subtitle">{{ heading }}</span>
  </header>

  <p v-if="error" class="banner banner-error">{{ error }}</p>
  <p v-if="loading" class="muted">Loading…</p>

  <template v-else-if="data">
    <p v-if="data.entries.length === 0" class="empty">
      Nothing due today. Add a routine to get started.
    </p>

    <template v-if="morning.length">
      <h2>Morning</h2>
      <TodayRow
        v-for="entry in morning"
        :key="entry.routine.id"
        :entry="entry"
        :busy="busyRoutine === entry.routine.id"
        @log="log(entry, $event)"
        @undo="undo(entry)"
      />
    </template>

    <template v-if="night.length">
      <h2>Night</h2>
      <TodayRow
        v-for="entry in night"
        :key="entry.routine.id"
        :entry="entry"
        :busy="busyRoutine === entry.routine.id"
        @log="log(entry, $event)"
        @undo="undo(entry)"
      />
    </template>
  </template>
</template>
