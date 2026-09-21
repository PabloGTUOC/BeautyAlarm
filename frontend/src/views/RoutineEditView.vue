<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import { WEEKDAYS } from '../dates'
import { useRoutinesStore } from '../stores/routines'
import type { TimePeriod } from '../types'

const props = defineProps<{ id?: string }>()
const router = useRouter()
const store = useRoutinesStore()

const NEW_PRODUCT = -1

const routineId = computed(() => (props.id ? Number(props.id) : null))
const isEdit = computed(() => routineId.value !== null)

const productId = ref<number>(NEW_PRODUCT)
const newName = ref('')
const newBrand = ref('')
const days = ref<number[]>([1, 2, 3, 4, 5, 6, 7])
const timePeriod = ref<TimePeriod>('morning')
const notificationTime = ref('')
const isActive = ref(true)
const endDate = ref('')

const loading = ref(true)
const saving = ref(false)
const error = ref<string | null>(null)

const creatingProduct = computed(() => productId.value === NEW_PRODUCT)

function toggleDay(iso: number): void {
  days.value = days.value.includes(iso)
    ? days.value.filter((d) => d !== iso)
    : [...days.value, iso].sort((a, b) => a - b)
}

function validate(): string | null {
  if (days.value.length === 0) return 'Pick at least one day.'
  if (creatingProduct.value && !newName.value.trim()) return 'Give the product a name.'
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
    const product = creatingProduct.value
      ? await store.findOrCreateProduct(newName.value, newBrand.value)
      : { id: productId.value }

    const payload = {
      product_id: product.id,
      days_of_week: days.value,
      time_period: timePeriod.value,
      // An empty time input means "no notification", which the API stores as null.
      notification_time: notificationTime.value || null,
      is_active: isActive.value,
      end_date: endDate.value || null
    }

    if (routineId.value !== null) await store.update(routineId.value, payload)
    else await store.create(payload)

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
      productId.value = routine.product_id
      days.value = [...routine.days_of_week]
      timePeriod.value = routine.time_period
      notificationTime.value = routine.notification_time?.slice(0, 5) ?? ''
      isActive.value = routine.is_active
      endDate.value = routine.end_date ?? ''
    } else if (store.activeProducts.length > 0) {
      productId.value = NEW_PRODUCT
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
    <label class="field">
      <span>Product</span>
      <select v-model.number="productId">
        <option :value="NEW_PRODUCT">＋ New product…</option>
        <option v-for="product in store.activeProducts" :key="product.id" :value="product.id">
          {{ product.name }}{{ product.brand ? ` — ${product.brand}` : '' }}
        </option>
      </select>
    </label>

    <template v-if="creatingProduct">
      <label class="field">
        <span>Name</span>
        <input v-model="newName" placeholder="Retinol serum" />
      </label>
      <label class="field">
        <span>Brand (optional)</span>
        <input v-model="newBrand" placeholder="CeraVe" />
      </label>
    </template>

    <div class="field">
      <span>Days</span>
      <div class="chips">
        <button
          v-for="day in WEEKDAYS"
          :key="day.iso"
          type="button"
          class="chip"
          :aria-pressed="days.includes(day.iso)"
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

    <label class="field">
      <span>Notify at (leave empty for no notification)</span>
      <input v-model="notificationTime" type="time" />
    </label>

    <label class="field">
      <span>Ends on (optional)</span>
      <input v-model="endDate" type="date" />
    </label>

    <label class="field row">
      <input v-model="isActive" type="checkbox" style="width: auto" />
      <span style="margin: 0">Active</span>
    </label>

    <div class="actions">
      <button class="btn btn-primary" type="submit" :disabled="saving">
        {{ saving ? 'Saving…' : 'Save' }}
      </button>
      <button class="btn" type="button" @click="router.push('/routines')">Cancel</button>
    </div>
  </form>
</template>
