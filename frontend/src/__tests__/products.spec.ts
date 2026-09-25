import { describe, expect, it } from 'vitest'
import { describeProducts } from '../products'
import type { Product } from '../types'

const p = (name: string, brand: string | null = null): Product => ({
  id: 1, name, brand, notes: null, archived_at: null
})

describe('describeProducts', () => {
  it('is empty for a routine with no products', () => {
    expect(describeProducts([])).toBe('')
  })

  it('names a single product, so a routine never shows only its own name', () => {
    expect(describeProducts([p('Gentle Cleanser')])).toBe('Gentle Cleanser')
  })

  it('carries the brand when there is one product to disambiguate', () => {
    expect(describeProducts([p('Gentle Cleanser', 'CeraVe')])).toBe('Gentle Cleanser · CeraVe')
  })

  it('joins several in application order and drops brands as noise', () => {
    const line = describeProducts([p('Hyaluronic Acid', 'The Ordinary'), p('Peptides'), p('Moisturizer')])
    expect(line).toBe('Hyaluronic Acid  →  Peptides  →  Moisturizer')
    expect(line).not.toContain('The Ordinary')
  })
})
