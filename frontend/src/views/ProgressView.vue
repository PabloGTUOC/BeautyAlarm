<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
import { addDays, fromLocalIsoDate, isoWeekday, toLocalIsoDate } from '../dates'
import type { CalendarDay, RoutineAdherence, Streak } from '../types'

const WEEKS = 12
const ROW_LABELS = ['Mon', '', 'Wed', '', 'Fri', '', 'Sun']

const streak = ref<Streak>({ current: 0, longest: 0 })
const days = ref<CalendarDay[]>([])
const adherence = ref<RoutineAdherence[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const hovered = ref<CalendarDay | null>(null)

/** Monday of the week containing `date`, so columns are whole weeks (D2). */
function startOfWeek(date: Date): Date {
  return addDays(date, -(isoWeekday(date) - 1))
}

const byDate = computed(() => new Map(days.value.map((day) => [day.date, day])))

/** Columns of 7 days, Monday at the top. */
const columns = computed(() => {
  const today = new Date()
  const first = startOfWeek(addDays(today, -7 * (WEEKS - 1)))
  const result: {
    date: string
    day: CalendarDay | null
    future: boolean
  }[][] = []
  for (let week = 0; week < WEEKS; week += 1) {
    const column = []
    for (let offset = 0; offset < 7; offset += 1) {
      const date = addDays(first, week * 7 + offset)
      const key = toLocalIsoDate(date)
      // Days before a routine's start_date come back with due = 0 from the API
      // (G28), which level() already renders as "nothing due".
      column.push({
        date: key,
        day: byDate.value.get(key) ?? null,
        future: date > today
      })
    }
    result.push(column)
  }
  return result
})

const monthLabels = computed(() =>
  columns.value.map((column, index) => {
    const first = fromLocalIsoDate(column[0].date)
    const previous = index > 0 ? fromLocalIsoDate(columns.value[index - 1][0].date) : null
    const changed = !previous || previous.getMonth() !== first.getMonth()
    return changed ? first.toLocaleDateString(undefined, { month: 'short' }) : ''
  })
)

/**
 * Sequential encoding of the day's completion ratio. Level 0 is "nothing was
 * due", which is not a low value on the same scale — it gets the surface, not
 * the lightest ramp step, so an empty day never reads as a missed one.
 */
function level(day: CalendarDay | null): number {
  if (!day || day.due === 0) return 0
  const ratio = day.completed / day.due
  if (ratio === 0) return 1
  if (ratio < 0.5) return 2
  if (ratio < 1) return 3
  return 4
}

function describe(day: CalendarDay | null, date: string): string {
  const readable = fromLocalIsoDate(date).toLocaleDateString(undefined, {
    weekday: 'short',
    day: 'numeric',
    month: 'short'
  })
  if (!day || day.due === 0) return `${readable}: nothing due`
  return `${readable}: ${day.completed} of ${day.due} done${day.skipped ? `, ${day.skipped} skipped` : ''}`
}

const recorded = computed(() => days.value.filter((day) => day.due > 0))

function percent(row: RoutineAdherence): number {
  return Math.round((row.completed / row.due) * 100)
}

onMounted(async () => {
  try {
    const today = new Date()
    const first = startOfWeek(addDays(today, -7 * (WEEKS - 1)))
    const [loadedStreak, loadedDays, loadedAdherence] = await Promise.all([
      api.streak(),
      api.calendar(toLocalIsoDate(first), toLocalIsoDate(today)),
      api.adherence(30)
    ])
    streak.value = loadedStreak
    days.value = loadedDays
    adherence.value = loadedAdherence
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <header class="app-header">
    <h1>Progress</h1>
  </header>

  <p v-if="error" class="banner banner-error">{{ error }}</p>
  <p v-if="loading" class="muted">Loading…</p>

  <template v-else>
    <p class="streak">
      <strong>{{ streak.current }}</strong>
      {{ streak.current === 1 ? 'day' : 'days' }} in a row<template v-if="streak.longest > streak.current">,
      best so far {{ streak.longest }}</template>.
    </p>

    <h2>Last {{ WEEKS }} weeks</h2>
    <div class="card viz-root">
      <div class="months" :style="{ gridTemplateColumns: `repeat(${WEEKS}, 1fr)` }">
        <span v-for="(label, index) in monthLabels" :key="index">{{ label }}</span>
      </div>

      <div class="heatmap">
        <div class="row-labels">
          <span v-for="(label, index) in ROW_LABELS" :key="index">{{ label }}</span>
        </div>
        <div class="grid" :style="{ gridTemplateColumns: `repeat(${WEEKS}, 1fr)` }">
          <template v-for="(column, weekIndex) in columns" :key="weekIndex">
            <button
              v-for="cell in column"
              :key="cell.date"
              type="button"
              class="cell"
              :class="[`level-${level(cell.day)}`, { future: cell.future }]"
              :aria-label="describe(cell.day, cell.date)"
              @click="hovered = cell.day"
              @mouseenter="hovered = cell.day"
              @focus="hovered = cell.day"
              @mouseleave="hovered = null"
              @blur="hovered = null"
            />
          </template>
        </div>
      </div>

      <p class="muted readout">
        {{ hovered ? describe(hovered, hovered.date) : 'Tap a day for details.' }}
      </p>

      <div class="legend muted">
        <span>Less</span>
        <i class="swatch level-1" />
        <i class="swatch level-2" />
        <i class="swatch level-3" />
        <i class="swatch level-4" />
        <span>More</span>
      </div>

      <details class="table-view">
        <summary class="muted">Show as table</summary>
        <table>
          <thead>
            <tr><th>Date</th><th>Due</th><th>Done</th><th>Skipped</th></tr>
          </thead>
          <tbody>
            <tr v-for="day in recorded" :key="day.date">
              <td>{{ day.date }}</td>
              <td>{{ day.due }}</td>
              <td>{{ day.completed }}</td>
              <td>{{ day.skipped }}</td>
            </tr>
          </tbody>
        </table>
        <p v-if="recorded.length === 0" class="muted">Nothing was due in this period.</p>
      </details>
    </div>

    <h2>Last 30 days</h2>
    <ul class="list">
      <li v-for="row in adherence" :key="row.routine_id">
        <div class="bar-head">
          <span class="bar-name">{{ row.routine_name }}</span>
          <span class="bar-value">{{ row.completed }}/{{ row.due }} · {{ percent(row) }}%</span>
        </div>
        <div class="bar" role="img" :aria-label="`${row.routine_name}: ${row.completed} of ${row.due} completed`">
          <div class="bar-fill" :style="{ inlineSize: percent(row) + '%' }" />
        </div>
      </li>
    </ul>
  </template>
</template>

<style scoped>
/*
 * Sequential ramp, single hue, light -> dark. Both modes validated with the
 * data-viz palette checker against this app's own surfaces: monotone lightness,
 * adjacent dL >= 0.06, and the lightest step clearing 2:1 so "due but not done"
 * never disappears into an empty day.
 */
.viz-root {
  --level-1: #d99eb4;
  --level-2: #c87693;
  --level-3: #b0426a;
  --level-4: #7d2c49;
  --level-empty: var(--surface-alt);
}

@media (prefers-color-scheme: dark) {
  :root:where(:not([data-theme='light'])) .viz-root {
    --level-1: #7d3c55;
    --level-2: #a04f72;
    --level-3: #c9799b;
    --level-4: #eaa8c0;
  }
}

:root[data-theme='dark'] .viz-root {
  --level-1: #7d3c55;
  --level-2: #a04f72;
  --level-3: #c9799b;
  --level-4: #eaa8c0;
}

/* One sentence instead of two big-number cards. The streak is a fact about
   the user, not a dashboard KPI. */
.streak {
  margin: 0.25rem 0 0.5rem;
  font-size: 1.0625rem;
  line-height: 1.45;
  color: var(--text-muted);
  text-wrap: pretty;
}
.streak strong {
  font-size: 2rem;
  font-weight: 680;
  line-height: 1;
  color: var(--text);
  letter-spacing: -0.02em;
  font-variant-numeric: tabular-nums;
  margin-inline-end: 0.15rem;
}

.bar-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.4rem;
}
.bar-name { font-size: 0.9375rem; font-weight: 550; min-width: 0; overflow-wrap: anywhere; }
.bar-value {
  flex: none;
  font-size: 0.8125rem;
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}
.bar {
  block-size: 6px;
  border-radius: 999px;
  background: var(--surface-alt);
  overflow: hidden;
}
.bar-fill {
  block-size: 100%;
  border-radius: 999px;
  background: var(--accent);
  transition: inline-size var(--medium) var(--ease);
}

.months,
.grid { display: grid; gap: 3px; }
.months { margin-left: 2.25rem; font-size: 0.6875rem; color: var(--text-muted); }

.heatmap { display: flex; gap: 0.5rem; }
.row-labels {
  display: grid;
  grid-template-rows: repeat(7, 1fr);
  gap: 3px;
  width: 1.75rem;
  font-size: 0.6875rem;
  color: var(--text-muted);
}
.grid { flex: 1; grid-template-rows: repeat(7, 1fr); grid-auto-flow: column; }

.cell {
  /* 24px floor: WCAG 2.5.8 target size. Eighty-four cells cannot each be 44px,
     and the same data is available in the table below. */
  aspect-ratio: 1;
  min-width: 0;
  min-block-size: 24px;
  padding: 0;
  border: none;
  border-radius: 3px;
  background: var(--level-empty);
  transition: transform var(--fast) var(--ease);
}
.cell:active { transform: scale(0.88); }
.cell.future { opacity: 0.35; }
.cell:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
.level-1 { background: var(--level-1); }
.level-2 { background: var(--level-2); }
.level-3 { background: var(--level-3); }
.level-4 { background: var(--level-4); }

.readout { margin: 0.75rem 0 0; min-height: 1.5rem; }
.legend { display: flex; align-items: center; gap: 0.25rem; font-size: 0.75rem; }
.swatch { width: 12px; height: 12px; border-radius: 3px; display: inline-block; }

.table-view { margin-top: 0.75rem; }
.table-view table { width: 100%; border-collapse: collapse; font-size: 0.8125rem; margin-top: 0.5rem; }
.table-view th, .table-view td { text-align: left; padding: 0.25rem 0.5rem; border-bottom: 1px solid var(--border); }


</style>
