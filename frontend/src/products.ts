import type { Product } from './types'

/**
 * The one-line description of what a routine actually applies, in application
 * order (D8a): "Hyaluronic Acid → Peptides → Moisturizer".
 *
 * Shared rather than reimplemented per row. Today's checklist, the Tracking
 * section and the routine list each grew their own copy and drifted: one hid
 * the line below two products, another never rendered it at all, so a routine
 * could show its name and nothing to put on your face.
 *
 * A single product carries its brand, which disambiguates it. Three products
 * with three brands is a wall of text, so brands are dropped there.
 */
export function describeProducts(products: Product[]): string {
  if (products.length === 0) return ''
  if (products.length === 1) {
    const only = products[0]
    return only.brand ? `${only.name} · ${only.brand}` : only.name
  }
  return products.map((p) => p.name).join('  →  ')
}
