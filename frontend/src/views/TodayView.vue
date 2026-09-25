<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import TodayRow from '../components/TodayRow.vue'
import TrackingRow from '../components/TrackingRow.vue'
import { api } from '../api'
import { fromLocalIsoDate, toLocalIsoDate } from '../dates'
import type { LogStatus, Streak, TodayEntry, TodayResponse, TrackingEntry } from '../types'

const data = ref<TodayResponse | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const busyRoutine = ref<number | null>(null)

/** Both fetched lazily, and only in the states that need them, so the common
 *  path (open, tick, close) stays a single request. */
const streak = ref<Streak | null>(null)
const hasAnyRoutine = ref<boolean | null>(null)

const entries = computed(() => data.value?.entries ?? [])
const morning = computed(() => entriesFor('morning'))
const night = computed(() => entriesFor('night'))
const tracking = computed(() => data.value?.tracking ?? [])

const doneCount = computed(
  () => entries.value.filter((e) => e.log?.status === 'completed').length
)

/** Nothing left pending. A skipped routine counts as dealt with: the day is
 *  over either way, and pretending otherwise would leave the screen stuck. */
const allActioned = computed(
  () => entries.value.length > 0 && entries.value.every((e) => e.log !== null)
)
/** Everything actually done, as opposed to partly skipped. Only this earns the
 *  streak line; celebrating a day of skips would be a lie. */
const allCompleted = computed(
  () => entries.value.length > 0 && entries.value.every((e) => e.log?.status === 'completed')
)
const skippedCount = computed(
  () => entries.value.filter((e) => e.log?.status === 'skipped').length
)

/** Nothing scheduled and nothing tracked. Distinct from "finished". */
const nothingToShow = computed(() => entries.value.length === 0 && tracking.value.length === 0)

const heading = computed(() => {
  // Falls back to the device's date so the one always-true piece of context
  // survives the loading and error states, where it is most reassuring.
  const iso = data.value?.date ?? toLocalIsoDate(new Date())
  return fromLocalIsoDate(iso).toLocaleDateString(undefined, {
    weekday: 'long',
    day: 'numeric',
    month: 'long'
  })
})

function entriesFor(period: 'morning' | 'night'): TodayEntry[] {
  return entries.value.filter((e) => e.routine.time_period === period)
}

function sectionCount(list: TodayEntry[]): string {
  const done = list.filter((e) => e.log?.status === 'completed').length
  return `${done}/${list.length}`
}

async function load(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    data.value = await api.today()

    // Only worth a round trip once the day is finished.
    if (allCompleted.value && streak.value === null) {
      streak.value = await api.streak().catch(() => null)
    }
    // Only worth asking when there is nothing at all to show: it is the one
    // case where "you have no routines" and "today is a rest day" look
    // identical but need opposite copy.
    if (nothingToShow.value && hasAnyRoutine.value === null) {
      hasAnyRoutine.value = await api
        .listRoutines()
        .then((r) => r.length > 0)
        .catch(() => null)
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
}

async function act(routineId: number, run: () => Promise<unknown>): Promise<void> {
  busyRoutine.value = routineId
  try {
    await run()
    await load()
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    busyRoutine.value = null
  }
}

const log = (entry: TodayEntry, status: LogStatus) =>
  act(entry.routine.id, () => api.logRoutine(entry.routine.id, status, data.value?.date))

/** Tracked routines are marked done for today; the counter resets to 0 (D11). */
const markTracked = (entry: TrackingEntry) =>
  act(entry.routine.id, () => api.logRoutine(entry.routine.id, 'completed', data.value?.date))

const undo = (entry: TodayEntry) =>
  entry.log ? act(entry.routine.id, () => api.deleteLog(entry.log!.id)) : Promise.resolve()

onMounted(load)
</script>

<template>
  <header class="app-header">
    <h1>Today</h1>
    <span class="subtitle">{{ heading }}</span>
  </header>

  <!-- role=alert so a screen reader announces the failure instead of waiting
       for focus to happen to land on it. -->
  <div v-if="error" class="banner banner-error" role="alert">
    <p class="banner-text">Could not reach the server.</p>
    <p class="banner-detail">{{ error }}</p>
    <button class="btn" :disabled="loading" @click="load">
      {{ loading ? 'Retrying…' : 'Try again' }}
    </button>
  </div>

  <p v-if="loading && !data" class="muted">Loading…</p>

  <template v-else-if="data">
    <!-- First run and a rest day look identical in the payload and need
         opposite copy, so they are told apart before either is shown. -->
    <div v-if="nothingToShow" class="empty">
      <template v-if="hasAnyRoutine === false">
        <p>No routines yet.</p>
        <p class="muted">Add your first one and it will show up here on the days it is due.</p>
        <RouterLink class="btn btn-primary" to="/routines/new">Add a routine</RouterLink>
      </template>
      <template v-else>
        <p>Nothing due today.</p>
        <p class="muted">A rest day. Your streak is safe.</p>
      </template>
    </div>

    <!-- The end of the daily path, and the only place the streak is visible
         without opening another tab. -->
    <div v-else-if="allActioned" class="finished" role="status">
      <p class="finished-line">
        {{ allCompleted ? 'All done for today.' : 'Nothing left for today.' }}
      </p>
      <p v-if="allCompleted && streak" class="muted">
        {{ streak.current }} {{ streak.current === 1 ? 'day' : 'days' }} in a row.
      </p>
      <p v-else-if="!allCompleted" class="muted">
        {{ doneCount }} done, {{ skippedCount }} skipped.
      </p>
    </div>

    <template v-if="morning.length">
      <h2 class="section-morning">
        Morning <span class="count">{{ sectionCount(morning) }}</span>
      </h2>
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
      <h2 class="section-night">
        Night <span class="count">{{ sectionCount(night) }}</span>
      </h2>
      <TodayRow
        v-for="entry in night"
        :key="entry.routine.id"
        :entry="entry"
        :busy="busyRoutine === entry.routine.id"
        @log="log(entry, $event)"
        @undo="undo(entry)"
      />
    </template>

    <!-- Always shown, not only when overdue: the counter is the feature (D11). -->
    <template v-if="tracking.length">
      <h2 class="section-tracking">Tracking</h2>
      <TrackingRow
        v-for="entry in tracking"
        :key="entry.routine.id"
        :entry="entry"
        :busy="busyRoutine === entry.routine.id"
        @done="markTracked(entry)"
      />
    </template>
  </template>
</template>

<style scoped>
.banner-error {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.5rem;
}
.banner-text { margin: 0; font-weight: 650; }
.banner-detail { margin: 0; font-size: 0.8125rem; opacity: 0.85; }

.empty { display: flex; flex-direction: column; align-items: center; gap: 0.5rem; }
.empty p { margin: 0; }
.empty .btn { margin-top: 0.75rem; text-decoration: none; }

/* Sits above the completed rows rather than replacing them: the list is still
   the record of what was done, this is the acknowledgement it was missing. */
.finished {
  padding: 1.25rem 1rem;
  margin-bottom: 0.25rem;
  text-align: center;
  background: var(--accent-surface);
  border: 1px solid var(--accent-border);
  border-radius: var(--radius);
}
.finished-line {
  margin: 0 0 0.2rem;
  font-size: 1.125rem;
  font-weight: 650;
  letter-spacing: -0.01em;
}
.finished .muted { margin: 0; }

/* Progress at a glance, without turning the heading into a metric. */
.count {
  margin-inline-start: auto;
  font-size: 0.8125rem;
  font-weight: 550;
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}
</style>
