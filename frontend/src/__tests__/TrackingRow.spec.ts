import { mount } from '@vue/test-utils'

/** Text with element boundaries collapsed to single spaces, so these assert
 *  what a reader sees rather than how the markup happens to be split. */
const read = (w: { text: () => string }) => w.text().replace(/\s+/g, ' ').trim()
import { describe, expect, it } from 'vitest'
import TrackingRow from '../components/TrackingRow.vue'
import type { TrackingEntry } from '../types'

function entry(overrides: Partial<TrackingEntry> = {}): TrackingEntry {
  return {
    routine: {
      id: 1,
      name: 'Haircut',
      kind: 'tracked',
      days_of_week: null,
      time_period: null,
      target_interval_days: 35,
      start_date: null,
      notification_time: '10:00:00',
      is_active: true,
      end_date: null,
      products: []
    },
    last_completed: '2026-09-01',
    days_since: 23,
    overdue: false,
    ...overrides
  }
}

describe('TrackingRow', () => {
  it('reports the elapsed days and the target', () => {
    const wrapper = mount(TrackingRow, { props: { entry: entry(), busy: false } })
    expect(read(wrapper)).toContain('Haircut')
    expect(read(wrapper)).toContain('23 days since the last one')
    expect(read(wrapper)).toContain('Target every 35 days')
  })

  it('does not say "1 days"', () => {
    const wrapper = mount(TrackingRow, {
      props: { entry: entry({ days_since: 1 }), busy: false }
    })
    expect(read(wrapper)).toContain('1 day since the last one')
    expect(read(wrapper)).not.toContain('1 days since')
  })

  it('says so when it was done today', () => {
    const wrapper = mount(TrackingRow, {
      props: { entry: entry({ days_since: 0 }), busy: false }
    })
    expect(read(wrapper)).toContain('Done today')
    expect(read(wrapper)).not.toContain('0 Done today')
  })

  it('admits when there is no baseline rather than inventing one', () => {
    const wrapper = mount(TrackingRow, {
      props: { entry: entry({ days_since: null, last_completed: null }), busy: false }
    })
    expect(read(wrapper)).toContain('Not recorded yet')
  })

  it('flags an overdue tracker', () => {
    const wrapper = mount(TrackingRow, {
      props: { entry: entry({ days_since: 40, overdue: true }), busy: false }
    })
    expect(read(wrapper)).toContain('Overdue')
    expect(wrapper.find('.card').classes()).toContain('overdue')
  })

  it('emits done when marked', async () => {
    const wrapper = mount(TrackingRow, { props: { entry: entry(), busy: false } })
    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('done')).toHaveLength(1)
  })

  it('disables the action while busy', () => {
    const wrapper = mount(TrackingRow, { props: { entry: entry(), busy: true } })
    expect(wrapper.find('button').attributes('disabled')).toBeDefined()
  })
})

describe('TrackingRow products', () => {
  it('shows what a tracked routine applies', () => {
    // Regression: TrackingRow had no reference to products at all, so a
    // "every 3 days, these three things" routine showed a name and a counter
    // and nothing to put on your face.
    const withProducts = entry()
    withProducts.routine.name = 'NightRoutineDay1'
    withProducts.routine.products = [
      { id: 1, name: 'Hyaluron', brand: null, notes: null, archived_at: null },
      { id: 2, name: 'Retinol 0.5%', brand: null, notes: null, archived_at: null },
      { id: 3, name: 'Moisturizer', brand: null, notes: null, archived_at: null }
    ]
    const wrapper = mount(TrackingRow, { props: { entry: withProducts, busy: false } })
    expect(read(wrapper)).toContain('Hyaluron → Retinol 0.5% → Moisturizer')
  })

  it('stays clean for a service with no products', () => {
    const wrapper = mount(TrackingRow, { props: { entry: entry(), busy: false } })
    expect(wrapper.find('.steps').exists()).toBe(false)
  })
})
