import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api } from '../api'
import type { Product, Routine, RoutineInput } from '../types'

export const useRoutinesStore = defineStore('routines', () => {
  const routines = ref<Routine[]>([])
  const products = ref<Product[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const activeProducts = computed(() => products.value.filter((p) => !p.archived_at))

  async function load(): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const [loadedRoutines, loadedProducts] = await Promise.all([
        api.listRoutines(),
        api.listProducts()
      ])
      routines.value = loadedRoutines
      products.value = loadedProducts
    } catch (err) {
      error.value = err instanceof Error ? err.message : String(err)
    } finally {
      loading.value = false
    }
  }

  /** Reuse a product with the same name and brand rather than creating a duplicate (G10). */
  async function findOrCreateProduct(name: string, brand: string): Promise<Product> {
    const wanted = name.trim().toLowerCase()
    const wantedBrand = brand.trim().toLowerCase()
    const existing = activeProducts.value.find(
      (p) => p.name.trim().toLowerCase() === wanted &&
        (p.brand ?? '').trim().toLowerCase() === wantedBrand
    )
    if (existing) return existing

    const created = await api.createProduct({ name: name.trim(), brand: brand.trim() || null })
    products.value = [...products.value, created]
    return created
  }

  async function create(input: RoutineInput): Promise<Routine> {
    const created = await api.createRoutine(input)
    routines.value = [...routines.value, created]
    return created
  }

  async function update(id: number, changes: Partial<RoutineInput>): Promise<Routine> {
    const updated = await api.updateRoutine(id, changes)
    routines.value = routines.value.map((r) => (r.id === id ? updated : r))
    return updated
  }

  async function remove(id: number): Promise<void> {
    await api.deleteRoutine(id)
    routines.value = routines.value.filter((r) => r.id !== id)
  }

  return {
    routines,
    products,
    activeProducts,
    loading,
    error,
    load,
    findOrCreateProduct,
    create,
    update,
    remove
  }
})
