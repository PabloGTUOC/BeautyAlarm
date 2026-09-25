<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import { WEEKDAYS, toLocalIsoDate } from '../dates'
import { useRoutinesStore } from '../stores/routines'
import type { RoutineInput, RoutineKind, TimePeriod } from '../types'

const props = defineProps<{ id?: string }>()
const router = useRouter()
const store = useRoutinesStore()

const routineId = computed(() => (props.id ? Number(props.id) : null))
const isEdit = computed(() => routineId.value !== null)

const name = ref('')
const kind = ref<RoutineKind>('scheduled')
/** Ordered: index 0 is applied first (D8a). */
const productIds = ref<number[]>([])
const pickerId = ref<number | ''>('')
const newName = ref('')
const newBrand = ref('')
const days = ref<number[]>([1, 2, 3, 4, 5, 6, 7])
const timePeriod = ref<TimePeriod>('morning')
const targetInterval = ref<number | ''>(35)
/** When this was last done, for a tracked routine. Recording it writes a log on
 *  that date rather than setting a marker: "I had a haircut on the 3rd" is a
 *  fact about a past occurrence, so it belongs in the history like any other. */
const lastDone = ref('')
const lastDoneOnLoad = ref('')
const notificationTime = ref('')
const isActive = ref(true)
const endDate = ref('')

const loading = ref(true)
const saving = ref(false)
const error = ref<string | null>(null)

const isTracked = computed(() => kind.value === 'tracked')
/** Today in the device's own zone, so the date picker cannot offer tomorrow. */
const todayIso = toLocalIsoDate(new Date())

/** Products already added drop out of the picker: the same product cannot
 *  appear twice in one routine. */
const available = computed(() =>
  store.activeProducts.filter((p) => !productIds.value.includes(p.id))
)

const chosen = computed(() =>
  productIds.value
    .map((id) => store.activeProducts.find((p) => p.id === id))
    .filter((p): p is NonNullable<typeof p> => p !== undefined)
)

function addProduct(): void {
  if (pickerId.value === '') return
  const id = Number(pickerId.value)
  if (!productIds.value.includes(id)) productIds.value = [...productIds.value, id]
  pickerId.value = ''
}

async function addNewProduct(): Promise<void> {
  if (!newName.value.trim()) {
    error.value = 'Give the product a name.'
    return
  }
  error.value = null
  try {
    const product = await store.findOrCreateProduct(newName.value, newBrand.value)
    if (!productIds.value.includes(product.id)) {
      productIds.value = [...productIds.value, product.id]
    }
    newName.value = ''
    newBrand.value = ''
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
}

function removeProduct(id: number): void {
  productIds.value = productIds.value.filter((p) => p !== id)
}

/** Application order is meaningful, so it is editable rather than sorted. */
function move(index: number, delta: number): void {
  const next = index + delta
  if (next < 0 || next >= productIds.value.length) return
  const copy = [...productIds.value]
  ;[copy[index], copy[next]] = [copy[next], copy[index]]
  productIds.value = copy
}

function toggleDay(iso: number): void {
  days.value = days.value.includes(iso)
    ? days.value.filter((d) => d !== iso)
    : [...days.value, iso].sort((a, b) => a - b)
}

function validate(): string | null {
  if (!name.value.trim()) return 'Give the routine a name.'
  if (isTracked.value) {
    if (targetInterval.value === '' || Number(targetInterval.value) < 1) {
      return 'Set how many days between occurrences.'
    }
    if (lastDone.value && lastDone.value > todayIso) {
      return 'You cannot have done it in the future.'
    }
  } else if (days.value.length === 0) {
    return 'Pick at least one day.'
  }
  return null
}

async function save(): Promise<void> {
  const problem = validate()
  if (problem) {
    error.value = problem
    return
  }

  saving.value = true
  error.value = null
  try {
    // The API rejects fields that contradict the kind (D11), so the unused
    // half is sent as null rather than left at its form default.
    const payload: RoutineInput = {
      name: name.value.trim(),
      kind: kind.value,
      product_ids: productIds.value,
      days_of_week: isTracked.value ? null : days.value,
      time_period: isTracked.value ? null : timePeriod.value,
      target_interval_days: isTracked.value ? Number(targetInterval.value) : null,
      start_date: null,
      // An empty time input means "no notification", which the API stores as null.
      notification_time: notificationTime.value || null,
      is_active: isActive.value,
      end_date: endDate.value || null
    }

    const saved =
      routineId.value !== null
        ? await store.update(routineId.value, payload)
        : await store.create(payload)

    // Written after the routine exists, and only when it changed, so editing a
    // routine for some other reason does not silently re-stamp its history.
    if (isTracked.value && lastDone.value && lastDone.value !== lastDoneOnLoad.value) {
      await api.logRoutine(saved.id, 'completed', lastDone.value)
    }

    router.push('/routines')
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  try {
    await store.load()
    if (routineId.value !== null) {
      const routine = await api.getRoutine(routineId.value)
      name.value = routine.name
      kind.value = routine.kind
      productIds.value = routine.products.map((p) => p.id)
      days.value = routine.days_of_week ? [...routine.days_of_week] : [1, 2, 3, 4, 5, 6, 7]
      timePeriod.value = routine.time_period ?? 'morning'
      targetInterval.value = routine.target_interval_days ?? 35
      notificationTime.value = routine.notification_time?.slice(0, 5) ?? ''
      isActive.value = routine.is_active
      endDate.value = routine.end_date ?? ''

      if (routine.kind === 'tracked') {
        // The tracking section already computes last_completed for every active
        // tracked routine, so the editor reads it from there rather than
        // needing its own endpoint.
        const tracking = (await api.today()).tracking
        const mine = tracking.find((entry) => entry.routine.id === routine.id)
        lastDone.value = mine?.last_completed ?? ''
        lastDoneOnLoad.value = lastDone.value
      }
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <header class="app-header">
    <h1>{{ isEdit ? 'Edit routine' : 'New routine' }}</h1>
  </header>

  <p v-if="error" class="banner banner-error">{{ error }}</p>
  <p v-if="loading" class="muted">Loading…</p>

  <form v-else @submit.prevent="save">
    <fieldset class="fieldset">
      <legend>What it is</legend>

      <label class="field">
        <span>Name</span>
        <input v-model="name" :placeholder="isTracked ? 'Haircut' : 'Night routine'" />
      </label>

      <div class="field">
        <span>Type</span>
        <div class="segmented" role="group" aria-label="Routine type">
          <button type="button" :aria-pressed="kind === 'scheduled'" @click="kind = 'scheduled'">
            On a schedule
          </button>
          <button type="button" :aria-pressed="kind === 'tracked'" @click="kind = 'tracked'">
            Every so often
          </button>
        </div>
        <small class="hint">
          {{
            isTracked
              ? 'Tracked by how long since you last did it: a haircut, a facial.'
              : 'Recurs on the weekdays you pick.'
          }}
        </small>
      </div>
    </fieldset>

    <fieldset class="fieldset">
      <legend>Products{{ isTracked ? ' (optional)' : '' }}</legend>

      <ol v-if="chosen.length" class="picked">
        <li v-for="(product, index) in chosen" :key="product.id">
          <span class="picked-name">
            {{ product.name }}<template v-if="product.brand"> · {{ product.brand }}</template>
          </span>
          <button
            type="button"
            class="btn btn-icon"
            :disabled="index === 0"
            :aria-label="`Move ${product.name} earlier`"
            @click="move(index, -1)"
          >↑</button>
          <button
            type="button"
            class="btn btn-icon"
            :disabled="index === chosen.length - 1"
            :aria-label="`Move ${product.name} later`"
            @click="move(index, 1)"
          >↓</button>
          <button
            type="button"
            class="btn btn-icon btn-danger"
            :aria-label="`Remove ${product.name}`"
            @click="removeProduct(product.id)"
          >✕</button>
        </li>
      </ol>
      <p v-else class="hint no-products">
        {{ isTracked ? 'None. This is an action, not a product.' : 'None added yet.' }}
      </p>

      <div class="stack">
        <div class="pair">
          <select v-model="pickerId" aria-label="Add an existing product">
            <option value="">Add an existing product…</option>
            <option v-for="product in available" :key="product.id" :value="product.id">
              {{ product.name }}{{ product.brand ? ` · ${product.brand}` : '' }}
            </option>
          </select>
          <button type="button" class="btn" :disabled="pickerId === ''" @click="addProduct">Add</button>
        </div>

        <!-- Stacked, not squeezed into one row: two inputs plus a button on a
             390px screen truncated both placeholders. -->
        <input v-model="newName" placeholder="…or type a new product" aria-label="New product name" />
        <div class="pair">
          <input v-model="newBrand" placeholder="Brand (optional)" aria-label="New product brand" />
          <button type="button" class="btn" @click="addNewProduct">Create</button>
        </div>
      </div>
    </fieldset>

    <fieldset class="fieldset">
      <legend>When</legend>

      <template v-if="!isTracked">
        <div class="field">
          <span>Days</span>
          <div class="chips weekdays">
            <button
              v-for="day in WEEKDAYS"
              :key="day.iso"
              type="button"
              class="chip"
              :aria-pressed="days.includes(day.iso)"
              :aria-label="day.long"
              @click="toggleDay(day.iso)"
            >
              {{ day.short }}
            </button>
          </div>
        </div>

        <label class="field">
          <span>Time of day</span>
          <select v-model="timePeriod">
            <option value="morning">Morning</option>
            <option value="night">Night</option>
          </select>
        </label>
      </template>

      <label v-else class="field">
        <span>Days between</span>
        <input v-model.number="targetInterval" type="number" min="1" max="3650" inputmode="numeric" />
        <small class="hint">
          Reminds you once it has been this long, then every other day.
        </small>
      </label>

      <label v-if="isTracked" class="field">
        <span>Last done on (optional)</span>
        <input v-model="lastDone" type="date" :max="todayIso" />
        <small class="hint">
          Set this when you start, so the count is right from day one. Recording
          it adds it to your history.
        </small>
      </label>

      <label class="field">
        <span>Notify at</span>
        <input v-model="notificationTime" type="time" />
        <small class="hint">Leave empty for no notification.</small>
      </label>

      <label v-if="!isTracked" class="field">
        <span>Ends on (optional)</span>
        <input v-model="endDate" type="date" />
      </label>

      <label class="field checkbox">
        <input v-model="isActive" type="checkbox" />
        <span>Active</span>
      </label>
    </fieldset>

    <div class="form-actions">
      <button class="btn" type="button" @click="router.push('/routines')">Cancel</button>
      <button class="btn btn-primary" type="submit" :disabled="saving">
        {{ saving ? 'Saving…' : 'Save routine' }}
      </button>
    </div>
  </form>
</template>

<style scoped>
.picked {
  list-style: none;
  counter-reset: step;
  margin: 0 0 0.75rem;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.picked li {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.25rem 0.25rem 0.75rem;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
}

/* Numbered, because the order is the instruction. */
.picked li::before {
  counter-increment: step;
  content: counter(step);
  flex: none;
  inline-size: 1.25rem;
  font-size: 0.8125rem;
  font-weight: 650;
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}

.picked-name {
  flex: 1;
  min-width: 0;
  font-size: 0.9375rem;
  line-height: 1.35;
  overflow-wrap: anywhere;
}

.no-products { margin: 0 0 0.75rem; }

.stack { display: flex; flex-direction: column; gap: 0.5rem; }
.stack input, .stack select {
  width: 100%;
  font: inherit;
  font-size: 1rem;
  min-block-size: var(--tap);
  padding: 0.55rem 0.75rem;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
  color: var(--text);
}
.stack input:focus, .stack select:focus { border-color: var(--accent); }
.pair { display: flex; gap: 0.5rem; }
.pair > :first-child { flex: 1; min-width: 0; }
.pair > .btn { flex: none; }

.checkbox {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  min-block-size: var(--tap);
}
.checkbox input {
  inline-size: 1.35rem;
  block-size: 1.35rem;
  min-block-size: 0;
  accent-color: var(--accent);
}
.checkbox > span { margin: 0; color: var(--text); font-size: 1rem; }
</style>
